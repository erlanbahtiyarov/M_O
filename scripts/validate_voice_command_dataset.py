"""Validate that the voice command dataset contains exactly 97 labeled rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_RECORDINGS = 97


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data") / "voice_commands_97.jsonl",
    )
    parser.add_argument("--expected-count", type=int, default=EXPECTED_RECORDINGS)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    rows = []
    with args.dataset.open("r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            payload["_line"] = line_number
            rows.append(payload)

    if len(rows) != args.expected_count:
        raise SystemExit(
            f"Dataset must contain exactly {args.expected_count} rows, found {len(rows)}"
        )

    missing_fields: list[str] = []
    for row in rows:
        for field in ("audio_path", "text", "intent", "canonical_text"):
            if field not in row or not str(row[field]).strip():
                missing_fields.append(f"line {row['_line']}: missing {field}")

    if missing_fields:
        preview = "\n".join(missing_fields[:10])
        raise SystemExit(f"Dataset validation failed:\n{preview}")

    print(
        json.dumps(
            {
                "rows": len(rows),
                "status": "ok",
                "dataset": str(args.dataset.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
