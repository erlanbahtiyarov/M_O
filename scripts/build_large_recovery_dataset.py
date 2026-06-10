"""Build a larger recovery dataset by combining synthetic noisy phrases with curated rows."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voice_control_pc.nlu import normalize_text


DEFAULT_PHRASES_PATH = PROJECT_ROOT / "data" / "noisy_command_phrases_97.json"
DEFAULT_CURATED_PATH = PROJECT_ROOT / "data" / "dataset_curated" / "recovery_dataset_86.jsonl"
DEFAULT_SYNTHETIC_MANIFEST_PATH = PROJECT_ROOT / "data" / "voice_commands_97.jsonl"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "dataset_curated" / "recovery_dataset_large.jsonl"

REPLACEMENTS = {
    "открой": ["крой", "окрой"],
    "запусти": ["запсти", "запустите"],
    "папку": ["папка", "папк"],
    "изображения": ["изобржения", "изображеня"],
    "документы": ["докумнты", "документы"],
    "настройки": ["настрйки", "настроки", "настреки"],
    "терминал": ["теримнал", "термннал"],
    "powershell": ["power shell", "powrshell"],
    "telegram": ["телеграм", "telegam"],
    "окно": ["окн", "акно"],
    "компьютер": ["компютер", "комп"],
    "загрузки": ["загруки", "загрузк"],
    "windows": ["window", "windws"],
}

OPTIONAL_WORDS = {
    "мне",
    "пожалуйста",
    "сейчас",
    "немедленно",
    "быстро",
    "папку",
    "это",
}

FILLERS = ["слушай", "эй", "быстро", "пожалуйста"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phrases", type=Path, default=DEFAULT_PHRASES_PATH)
    parser.add_argument("--curated", type=Path, default=DEFAULT_CURATED_PATH)
    parser.add_argument("--synthetic-manifest", type=Path, default=DEFAULT_SYNTHETIC_MANIFEST_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--variants-per-phrase", type=int, default=40)
    parser.add_argument("--variants-per-curated-train-row", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def load_json_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON array")
    return [dict(item) for item in payload]


def load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def build_audio_path_map(rows: list[dict[str, Any]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in rows:
        canonical_text = normalize_text(str(row.get("canonical_text", "")))
        audio_path = str(row.get("audio_path", "")).strip()
        if canonical_text and audio_path:
            mapping[canonical_text] = audio_path
    return mapping


def mutate_word(word: str, rng: random.Random) -> str:
    normalized = normalize_text(word)
    if normalized in REPLACEMENTS:
        return rng.choice(REPLACEMENTS[normalized])
    if len(word) >= 5:
        op = rng.choice(["drop", "swap", "duplicate"])
        if op == "drop":
            index = rng.randrange(1, len(word))
            return word[:index] + word[index + 1 :]
        if op == "swap" and len(word) >= 4:
            index = rng.randrange(1, len(word) - 1)
            chars = list(word)
            chars[index], chars[index + 1] = chars[index + 1], chars[index]
            return "".join(chars)
        if op == "duplicate":
            index = rng.randrange(1, len(word))
            return word[:index] + word[index] + word[index:]
    return word


def mutate_text(base_text: str, rng: random.Random) -> str:
    text = normalize_text(base_text)
    words = text.split()
    if not words:
        return text

    operation_count = rng.randint(1, 3)
    for _ in range(operation_count):
        operation = rng.choice(
            [
                "mutate_word",
                "drop_optional_word",
                "drop_first_letter",
                "prepend_filler",
                "append_filler",
            ]
        )
        if operation == "mutate_word":
            index = rng.randrange(len(words))
            words[index] = mutate_word(words[index], rng)
        elif operation == "drop_optional_word":
            candidates = [index for index, word in enumerate(words) if word in OPTIONAL_WORDS]
            if candidates:
                del words[rng.choice(candidates)]
        elif operation == "drop_first_letter":
            first = words[0]
            if len(first) > 3:
                words[0] = first[1:]
        elif operation == "prepend_filler":
            words.insert(0, rng.choice(FILLERS))
        elif operation == "append_filler":
            words.append(rng.choice(FILLERS))

        words = [word for word in words if word]
        if not words:
            words = text.split()

    return normalize_text(" ".join(words))


def build_phrase_variants(
    canonical_text: str,
    noisy_text: str,
    count: int,
    rng: random.Random,
) -> list[str]:
    variants = {
        normalize_text(noisy_text),
        normalize_text(canonical_text),
    }
    base_candidates = [canonical_text, noisy_text]
    target_count = max(count, 2)
    while len(variants) < target_count:
        base_text = rng.choice(base_candidates)
        variants.add(mutate_text(base_text, rng))
    return [variant for variant in variants if variant]


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    rng = random.Random(args.seed)

    phrase_rows = load_json_rows(args.phrases)
    curated_rows = load_jsonl_rows(args.curated)
    synthetic_manifest_rows = (
        load_jsonl_rows(args.synthetic_manifest) if args.synthetic_manifest.exists() else []
    )
    audio_path_map = build_audio_path_map(synthetic_manifest_rows)

    complete_curated_rows = [
        row
        for row in curated_rows
        if str(row.get("text", "")).strip()
        and str(row.get("intent", "")).strip()
        and str(row.get("canonical_text", "")).strip()
    ]

    output_rows: list[dict[str, Any]] = []

    for row in complete_curated_rows:
        item = dict(row)
        item.setdefault("source", "curated_real")
        output_rows.append(item)

    synthetic_count = 0
    for row in phrase_rows:
        canonical_text = str(row["canonical_text"])
        noisy_text = str(row.get("noisy_text") or canonical_text)
        variants = build_phrase_variants(
            canonical_text=canonical_text,
            noisy_text=noisy_text,
            count=args.variants_per_phrase,
            rng=rng,
        )
        audio_path = audio_path_map.get(
            normalize_text(canonical_text),
            f"synthetic://{row['id']}.wav",
        )
        for index, variant in enumerate(variants, start=1):
            output_rows.append(
                {
                    "id": f"syn_{row['id']}_{index:03d}",
                    "split": "train",
                    "audio_path": audio_path,
                    "source": "synthetic_augmentation",
                    "voice": "synthetic",
                    "original_name": f"synthetic_{row['id']}.wav",
                    "text": variant,
                    "intent": row["intent"],
                    "canonical_text": canonical_text,
                    "transcript_asr": variant,
                    "language": "ru",
                    "matched_example": canonical_text,
                    "prediction_confidence": 1.0,
                    "review_status": "auto_generated",
                }
            )
            synthetic_count += 1

    curated_train_rows = [
        row for row in complete_curated_rows if str(row.get("split", "")).strip() == "train"
    ]
    augmented_real_count = 0
    for row in curated_train_rows:
        for index in range(args.variants_per_curated_train_row):
            variant = mutate_text(str(row["text"]), rng)
            output_rows.append(
                {
                    "id": f"{row.get('id', 'curated')}_aug_{index + 1:02d}",
                    "split": "train",
                    "audio_path": str(row.get("audio_path", "augmented://real")),
                    "source": "curated_augmentation",
                    "voice": str(row.get("voice", "unknown")),
                    "original_name": str(row.get("original_name", "")),
                    "text": variant,
                    "intent": str(row["intent"]),
                    "canonical_text": str(row["canonical_text"]),
                    "transcript_asr": variant,
                    "language": "ru",
                    "matched_example": str(row.get("matched_example") or row["canonical_text"]),
                    "prediction_confidence": 1.0,
                    "review_status": "auto_generated",
                }
            )
            augmented_real_count += 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        for row in output_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    split_counts: dict[str, int] = {}
    intent_counts: dict[str, int] = {}
    for row in output_rows:
        split = str(row.get("split", "train"))
        intent = str(row.get("intent", ""))
        split_counts[split] = split_counts.get(split, 0) + 1
        intent_counts[intent] = intent_counts.get(intent, 0) + 1

    print(
        json.dumps(
            {
                "rows": len(output_rows),
                "synthetic_rows": synthetic_count,
                "augmented_real_rows": augmented_real_count,
                "curated_rows": len(complete_curated_rows),
                "split_counts": split_counts,
                "intent_counts": intent_counts,
                "output_path": str(args.output.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
