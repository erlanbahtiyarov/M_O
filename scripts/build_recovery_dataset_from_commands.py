"""Generate a starter JSONL dataset for command recovery from commands.yaml."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voice_control_pc.config import load_config_bundle
from voice_control_pc.nlu import normalize_text


def degrade_phrase(phrase: str) -> list[str]:
    normalized = normalize_text(phrase)
    variants = {normalized}
    words = normalized.split()

    if words:
        first = words[0]
        if len(first) > 3:
            words_variant = words.copy()
            words_variant[0] = first[2:]
            variants.add(" ".join(words_variant))

    variants.add(normalized.replace("папку ", ""))
    variants.add(normalized.replace("сделай ", ""))
    variants.add(normalized.replace("открой ", "крой ", 1))
    variants.add(normalized.replace("скриншот", "скрин"))
    variants.add(normalized.replace("компьютер", "комп"))
    variants.add(normalized.replace("рабочий стол", "стол"))
    variants.add(normalized.replace("диспетчер задач", "диспетчер"))
    return [variant.strip() for variant in variants if variant.strip()]


def main() -> int:
    config = load_config_bundle(PROJECT_ROOT)
    output_path = PROJECT_ROOT / "data" / "command_recovery_train.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    for spec in config.commands.intents:
        canonical = spec.examples[0]
        for example in spec.examples:
            for degraded in degrade_phrase(example):
                rows.append(
                    {
                        "text": degraded,
                        "intent": spec.intent,
                        "canonical_text": canonical,
                    }
                )

    with output_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps({"rows": len(rows), "output_path": str(output_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
