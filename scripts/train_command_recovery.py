"""Train local neural command recovery model from JSONL dataset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voice_control_pc.ml.command_recovery import load_training_rows, train_command_recovery_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "data" / "dataset_curated" / "recovery_dataset_86.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "models" / "command_recovery.pt",
    )
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--num-features", type=int, default=4096)
    parser.add_argument(
        "--expected-count",
        type=int,
        default=None,
        help="Optional hard check for dataset row count, e.g. 86",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    rows = load_training_rows(args.dataset)
    if args.expected_count is not None and len(rows) != args.expected_count:
        raise SystemExit(
            f"Training dataset must contain exactly {args.expected_count} rows, found {len(rows)}"
        )

    invalid_rows = [
        index + 1
        for index, row in enumerate(rows)
        if not str(row.get("text", "")).strip()
        or not str(row.get("intent", "")).strip()
        or not str(row.get("canonical_text", "")).strip()
    ]
    if invalid_rows:
        preview = ", ".join(str(item) for item in invalid_rows[:10])
        raise SystemExit(
            f"Dataset contains incomplete rows. First invalid lines: {preview}"
        )

    summary = train_command_recovery_model(
        rows=rows,
        output_path=args.output,
        hidden_dim=args.hidden_dim,
        num_features=args.num_features,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
