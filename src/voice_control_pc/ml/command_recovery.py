"""Local neural recovery for imperfect ASR command transcripts."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from voice_control_pc.models import CommandCatalog, IntentMatch, NluSettings
from voice_control_pc.nlu import normalize_text


def _require_torch():
    try:
        import torch
        from torch import nn
    except ImportError as error:
        raise RuntimeError(
            "Для neural recovery требуется torch. Установите: pip install -e .[ml]"
        ) from error
    return torch, nn


class HashedTextVectorizer:
    def __init__(self, num_features: int = 4096, char_ngram_range: tuple[int, int] = (2, 5)):
        self.num_features = num_features
        self.char_ngram_range = char_ngram_range

    def _hash(self, value: str) -> int:
        digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "little") % self.num_features

    def _iter_features(self, text: str):
        normalized = normalize_text(text)
        if not normalized:
            return

        for word in normalized.split():
            yield f"word:{word}"

        padded = f"  {normalized}  "
        min_n, max_n = self.char_ngram_range
        for size in range(min_n, max_n + 1):
            for index in range(len(padded) - size + 1):
                yield f"char:{padded[index:index + size]}"

    def transform_one(self, text: str):
        torch, _nn = _require_torch()
        vector = torch.zeros(self.num_features, dtype=torch.float32)
        counts = Counter(self._hash(feature) for feature in self._iter_features(text))
        for feature_index, count in counts.items():
            vector[feature_index] = float(count)
        return vector

    def transform_many(self, texts: list[str]):
        torch, _nn = _require_torch()
        if not texts:
            return torch.empty(0, self.num_features, dtype=torch.float32)
        return torch.stack([self.transform_one(text) for text in texts])


def build_network(input_dim: int, output_dim: int, hidden_dim: int, dropout: float):
    _torch, nn = _require_torch()
    return nn.Sequential(
        nn.Linear(input_dim, hidden_dim),
        nn.ReLU(),
        nn.Dropout(dropout),
        nn.Linear(hidden_dim, hidden_dim),
        nn.ReLU(),
        nn.Dropout(dropout),
        nn.Linear(hidden_dim, output_dim),
    )


def sequence_similarity(left: str, right: str) -> float:
    left_tokens = set(normalize_text(left).split())
    right_tokens = set(normalize_text(right).split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


class NeuralCommandRecovery:
    def __init__(
        self,
        model,
        vectorizer: HashedTextVectorizer,
        intent_labels: list[str],
        canonical_texts_by_intent: dict[str, list[str]],
        confidence_threshold: float,
    ):
        self.model = model
        self.vectorizer = vectorizer
        self.intent_labels = intent_labels
        self.canonical_texts_by_intent = canonical_texts_by_intent
        self.confidence_threshold = confidence_threshold
        self.model.eval()

    @classmethod
    def load(cls, model_path: Path, confidence_threshold: float):
        torch, _nn = _require_torch()
        checkpoint = torch.load(model_path, map_location="cpu")
        vectorizer = HashedTextVectorizer(
            num_features=checkpoint["num_features"],
            char_ngram_range=tuple(checkpoint["char_ngram_range"]),
        )
        model = build_network(
            input_dim=checkpoint["num_features"],
            output_dim=len(checkpoint["intent_labels"]),
            hidden_dim=checkpoint["hidden_dim"],
            dropout=checkpoint["dropout"],
        )
        model.load_state_dict(checkpoint["state_dict"])
        return cls(
            model=model,
            vectorizer=vectorizer,
            intent_labels=checkpoint["intent_labels"],
            canonical_texts_by_intent=checkpoint["canonical_texts_by_intent"],
            confidence_threshold=confidence_threshold,
        )

    def predict(self, text: str) -> dict[str, Any]:
        torch, _nn = _require_torch()
        features = self.vectorizer.transform_many([text])
        with torch.no_grad():
            logits = self.model(features)
            probabilities = torch.softmax(logits, dim=1)[0]
            confidence, predicted_index = torch.max(probabilities, dim=0)

        predicted_intent = self.intent_labels[predicted_index.item()]
        canonical_text = self._retrieve_canonical_text(text, predicted_intent)
        return {
            "intent": predicted_intent,
            "confidence": float(confidence.item()),
            "canonical_text": canonical_text,
            "scores": {
                label: float(probabilities[index].item())
                for index, label in enumerate(self.intent_labels)
            },
        }

    def enhance_match(self, raw_text: str, match: IntentMatch) -> IntentMatch:
        prediction = self.predict(raw_text)
        if prediction["confidence"] < self.confidence_threshold:
            return match

        if match.intent is None or prediction["intent"] != match.intent:
            match.intent = prediction["intent"]
        match.corrected_text = prediction["canonical_text"]
        match.correction_confidence = round(prediction["confidence"], 4)
        return match

    def _retrieve_canonical_text(self, raw_text: str, intent: str) -> str:
        candidates = self.canonical_texts_by_intent.get(intent, [])
        if not candidates:
            return normalize_text(raw_text)
        best_candidate = candidates[0]
        best_score = -1.0
        for candidate in candidates:
            score = sequence_similarity(raw_text, candidate)
            if normalize_text(raw_text) in normalize_text(candidate):
                score += 0.2
            if score > best_score:
                best_score = score
                best_candidate = candidate
        return best_candidate


def build_canonical_texts_from_commands(commands: CommandCatalog) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for spec in commands.intents:
        mapping[spec.intent] = list(spec.examples)
    return mapping


def load_training_rows(dataset_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with dataset_path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if "text" not in payload or "intent" not in payload:
                continue
            rows.append(payload)
    return rows


def train_command_recovery_model(
    rows: list[dict[str, Any]],
    output_path: Path,
    hidden_dim: int = 256,
    num_features: int = 4096,
    epochs: int = 25,
    batch_size: int = 32,
    learning_rate: float = 1e-3,
) -> dict[str, Any]:
    torch, nn = _require_torch()

    filtered_rows = [row for row in rows if row.get("intent")]
    if not filtered_rows:
        raise ValueError("Training dataset is empty after filtering")

    intent_labels = sorted({str(row["intent"]) for row in filtered_rows})
    intent_to_index = {label: index for index, label in enumerate(intent_labels)}

    canonical_texts_by_intent: dict[str, list[str]] = {}
    for row in filtered_rows:
        intent = str(row["intent"])
        canonical_text = str(row.get("canonical_text") or row.get("text"))
        canonical_texts_by_intent.setdefault(intent, [])
        if canonical_text not in canonical_texts_by_intent[intent]:
            canonical_texts_by_intent[intent].append(canonical_text)

    vectorizer = HashedTextVectorizer(num_features=num_features)
    model = build_network(
        input_dim=num_features,
        output_dim=len(intent_labels),
        hidden_dim=hidden_dim,
        dropout=0.15,
    )

    train_texts = [str(row["text"]) for row in filtered_rows]
    train_targets = [intent_to_index[str(row["intent"])] for row in filtered_rows]

    features = vectorizer.transform_many(train_texts)
    targets = torch.tensor(train_targets, dtype=torch.long)

    dataset = torch.utils.data.TensorDataset(features, targets)
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    history: list[dict[str, Any]] = []
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for batch_features, batch_targets in dataloader:
            optimizer.zero_grad()
            logits = model(batch_features)
            loss = criterion(logits, batch_targets)
            loss.backward()
            optimizer.step()

            total_loss += float(loss.item())
            predicted = logits.argmax(dim=1)
            correct += int((predicted == batch_targets).sum().item())
            total += int(batch_targets.numel())

        history.append(
            {
                "epoch": epoch,
                "loss": round(total_loss / max(len(dataloader), 1), 4),
                "accuracy": round(correct / max(total, 1), 4),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "intent_labels": intent_labels,
            "canonical_texts_by_intent": canonical_texts_by_intent,
            "num_features": num_features,
            "char_ngram_range": list(vectorizer.char_ngram_range),
            "hidden_dim": hidden_dim,
            "dropout": 0.15,
        },
        output_path,
    )

    return {
        "rows": len(filtered_rows),
        "intent_count": len(intent_labels),
        "output_path": str(output_path),
        "history": history,
    }


def maybe_load_recovery_model(
    settings: NluSettings, commands: CommandCatalog, project_root: Path
) -> NeuralCommandRecovery | None:
    if not settings.neural_recovery_enabled:
        return None

    model_path = project_root / settings.neural_model_path
    if not model_path.exists():
        return None

    recovery = NeuralCommandRecovery.load(
        model_path=model_path,
        confidence_threshold=settings.neural_confidence,
    )

    fallback_mapping = build_canonical_texts_from_commands(commands)
    for intent, examples in fallback_mapping.items():
        recovery.canonical_texts_by_intent.setdefault(intent, examples)
    return recovery
