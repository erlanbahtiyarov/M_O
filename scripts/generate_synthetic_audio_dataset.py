"""Generate 97 synthetic Russian audio command recordings using local Windows TTS."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHRASES_PATH = PROJECT_ROOT / "data" / "synthetic_command_phrases_97.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "audio_commands"
MANIFEST_PATH = PROJECT_ROOT / "data" / "voice_commands_97.jsonl"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phrases", type=Path, default=PHRASES_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    return parser


def powershell_escape(value: str) -> str:
    return value.replace("'", "''")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    phrases = json.loads(args.phrases.read_text(encoding="utf-8"))
    if len(phrases) != 97:
        raise SystemExit(f"Expected exactly 97 phrases, got {len(phrases)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, str]] = []

    for index, item in enumerate(phrases):
        audio_path = args.output_dir / f"{item['id']}.wav"
        rate = [-2, -1, 0, 1, 2][index % 5]
        volume = [90, 95, 100][index % 3]

        command = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.SelectVoice('Microsoft Irina Desktop'); "
            f"$s.Rate = {rate}; "
            f"$s.Volume = {volume}; "
            f"$s.SetOutputToWaveFile('{powershell_escape(str(audio_path))}'); "
            f"$s.Speak('{powershell_escape(item['canonical_text'])}'); "
            "$s.Dispose()"
        )

        from subprocess import run

        result = run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise SystemExit(
                f"Failed to synthesize {audio_path.name}: {result.stderr.strip() or result.stdout.strip()}"
            )

        manifest_rows.append(
            {
                "audio_path": str(audio_path.resolve()),
                "text": item["canonical_text"],
                "intent": item["intent"],
                "canonical_text": item["canonical_text"],
                "language": "ru",
                "speaker_type": "synthetic_tts",
                "voice": "Microsoft Irina Desktop",
            }
        )

    with args.manifest.open("w", encoding="utf-8") as fh:
        for row in manifest_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "rows": len(manifest_rows),
                "output_dir": str(args.output_dir.resolve()),
                "manifest": str(args.manifest.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
