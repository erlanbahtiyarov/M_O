"""Build a draft recovery-training JSONL from the curated purchased audio corpus."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


DEFAULT_INPUT_MANIFEST = PROJECT_ROOT / "data" / "dataset_curated" / "dataset_manifest.jsonl"
DEFAULT_OUTPUT_DATASET = PROJECT_ROOT / "data" / "dataset_curated" / "recovery_dataset_86.jsonl"
DEFAULT_COMMANDS = PROJECT_ROOT / "data" / "synthetic_command_phrases_97.json"


@dataclass
class SimpleAsrSettings:
    model_name: str = "small"
    model_path: str = "models"
    device: str = "cpu"
    compute_type: str = "int8"
    beam_size: int = 5
    language: str = "ru"
    vad_filter: bool = True
    condition_on_previous_text: bool = False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_INPUT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DATASET)
    parser.add_argument("--commands", type=Path, default=DEFAULT_COMMANDS)
    parser.add_argument(
        "--expected-count",
        type=int,
        default=86,
        help="Expected row count for the curated purchased dataset",
    )
    parser.add_argument(
        "--skip-asr",
        action="store_true",
        help="Do not run Faster-Whisper; use transcript_asr from manifest if it exists",
    )
    parser.add_argument(
        "--force-asr",
        action="store_true",
        help="Always re-run ASR even if transcript_asr is already present in manifest",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.45,
        help="Below this score intent/canonical_text stay empty and row is marked for review",
    )
    return parser


def load_manifest_rows(manifest_path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with manifest_path.open("r", encoding="utf-8-sig") as fh:
        for line_number, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            payload["_line"] = line_number
            rows.append(payload)
    return rows


def load_command_examples(commands_path: Path) -> list[dict[str, str]]:
    with commands_path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    rows: list[dict[str, str]] = []
    for item in payload:
        intent = str(item.get("intent", "")).strip()
        canonical_text = str(item.get("canonical_text", "")).strip()
        if intent and canonical_text:
            rows.append({"intent": intent, "canonical_text": canonical_text})
    return rows


def normalize_text(text: str) -> str:
    normalized = text.lower().replace("ё", "е").strip()
    normalized = re.sub(r"[^\w\s-]", " ", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def token_overlap_score(left: str, right: str) -> float:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return intersection / union


def predict_from_examples(
    text: str,
    command_examples: list[dict[str, str]],
) -> dict[str, str | float]:
    normalized_text = normalize_text(text)
    best_intent = ""
    best_canonical = ""
    best_score = 0.0

    for item in command_examples:
        canonical_text = normalize_text(item["canonical_text"])
        if normalized_text == canonical_text:
            score = 1.0
        elif normalized_text.startswith(canonical_text) or canonical_text.startswith(normalized_text):
            score = 0.92
        else:
            score = token_overlap_score(normalized_text, canonical_text)
        if score > best_score:
            best_score = score
            best_intent = item["intent"]
            best_canonical = canonical_text

    return {
        "intent": best_intent,
        "canonical_text": best_canonical,
        "confidence": round(best_score, 4),
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    rows = load_manifest_rows(args.manifest)
    if args.expected_count is not None and len(rows) != args.expected_count:
        raise SystemExit(
            f"Expected {args.expected_count} rows in {args.manifest}, found {len(rows)}"
        )

    command_examples = load_command_examples(args.commands)
    if not command_examples:
        raise SystemExit(f"No command examples found in {args.commands}")

    transcribe_file = None
    if not args.skip_asr:
        from faster_whisper import WhisperModel

        settings = SimpleAsrSettings()
        model = WhisperModel(
            settings.model_name,
            device=settings.device,
            compute_type=settings.compute_type,
            download_root=str((PROJECT_ROOT / settings.model_path).resolve()),
        )

        def transcribe_file(audio_path: Path) -> str:
            segments, _info = model.transcribe(
                str(audio_path),
                beam_size=settings.beam_size,
                language=settings.language,
                vad_filter=settings.vad_filter,
                condition_on_previous_text=settings.condition_on_previous_text,
            )
            return " ".join(segment.text.strip() for segment in segments).strip()

    prepared_rows: list[dict[str, object]] = []
    auto_labeled = 0
    needs_review = 0

    for row in rows:
        audio_path = Path(str(row["audio_path"])).resolve()
        transcript = str(row.get("transcript_asr", "") or "").strip()
        if transcribe_file is not None and (args.force_asr or not transcript):
            transcript = transcribe_file(audio_path)

        normalized_transcript = normalize_text(transcript)
        prediction = predict_from_examples(normalized_transcript, command_examples)

        predicted_intent = ""
        predicted_canonical = ""
        predicted_confidence = 0.0
        matched_example = ""
        review_status = "needs_review"

        if normalized_transcript:
            matched_example = str(prediction["canonical_text"])
            predicted_confidence = float(prediction["confidence"])
            if prediction["intent"] and predicted_confidence >= args.min_confidence:
                predicted_intent = str(prediction["intent"])
                predicted_canonical = str(prediction["canonical_text"])
                review_status = "auto_labeled"
                auto_labeled += 1
            else:
                needs_review += 1
        else:
            needs_review += 1

        prepared_rows.append(
            {
                "id": row.get("id", ""),
                "split": row.get("split", ""),
                "audio_path": str(audio_path),
                "source": row.get("source", ""),
                "voice": row.get("voice", ""),
                "original_name": row.get("original_name", ""),
                "text": normalized_transcript,
                "intent": predicted_intent,
                "canonical_text": predicted_canonical,
                "transcript_asr": normalized_transcript,
                "language": row.get("language", "ru"),
                "matched_example": matched_example,
                "prediction_confidence": predicted_confidence,
                "review_status": review_status,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        for row in prepared_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "rows": len(prepared_rows),
                "output_path": str(args.output.resolve()),
                "asr_enabled": not args.skip_asr,
                "auto_labeled": auto_labeled,
                "needs_review": needs_review,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
