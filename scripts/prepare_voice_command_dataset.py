"""Prepare a JSONL dataset from exactly 97 voice command recordings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voice_control_pc.asr import FasterWhisperTranscriber
from voice_control_pc.config import load_config_bundle


EXPECTED_RECORDINGS = 97
SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "audio_commands",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "voice_commands_97.jsonl",
    )
    parser.add_argument("--expected-count", type=int, default=EXPECTED_RECORDINGS)
    parser.add_argument("--skip-asr", action="store_true")
    return parser


def discover_audio_files(audio_dir: Path) -> list[Path]:
    return sorted(
        path for path in audio_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = load_config_bundle(PROJECT_ROOT)
    audio_files = discover_audio_files(args.audio_dir)
    if len(audio_files) != args.expected_count:
        raise SystemExit(
            f"Expected exactly {args.expected_count} recordings, found {len(audio_files)} in {args.audio_dir}"
        )

    transcriber = None
    if not args.skip_asr:
        transcriber = FasterWhisperTranscriber(config.settings.asr)

    rows: list[dict[str, str]] = []
    for audio_path in audio_files:
        transcript = ""
        if transcriber is not None:
            transcript = transcriber.transcribe_file(audio_path)

        rows.append(
            {
                "audio_path": str(audio_path.resolve()),
                "text": transcript,
                "intent": "",
                "canonical_text": "",
                "language": "ru",
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "rows": len(rows),
                "output_path": str(args.output.resolve()),
                "transcribed": not args.skip_asr,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
