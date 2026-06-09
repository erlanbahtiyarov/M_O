"""Validate a voice command dataset used for recovery/intention training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data") / "dataset_curated" / "recovery_dataset_86.jsonl",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=None,
        help="Optional hard check for dataset row count, e.g. 86",
    )
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="Allow incomplete intent/canonical_text fields for draft datasets",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    rows = []
    with args.dataset.open("r", encoding="utf-8-sig") as fh:
        for line_number, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            payload["_line"] = line_number
            rows.append(payload)

    if args.expected_count is not None and len(rows) != args.expected_count:
        raise SystemExit(
            f"Dataset must contain exactly {args.expected_count} rows, found {len(rows)}"
        )

    missing_fields: list[str] = []
    for row in rows:
        required_fields = ("audio_path",)
        if not args.allow_draft:
            required_fields += ("text", "intent", "canonical_text")
        for field in required_fields:
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
                "draft_mode": args.allow_draft,
                "dataset": str(args.dataset.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
