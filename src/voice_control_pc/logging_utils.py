"""Logging helpers."""

from __future__ import annotations

import json
import logging
from pathlib import Path


def setup_logging(level: str, text_log_path: Path, jsonl_log_path: Path) -> logging.Logger:
    logger = logging.getLogger("voice_control_pc")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    text_log_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_log_path.parent.mkdir(parents=True, exist_ok=True)

    text_handler = logging.FileHandler(text_log_path, encoding="utf-8")
    text_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.addHandler(text_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))
    logger.addHandler(console_handler)

    jsonl_handler = JsonlHandler(jsonl_log_path)
    logger.addHandler(jsonl_handler)
    return logger


class JsonlHandler(logging.Handler):
    def __init__(self, path: Path):
        super().__init__()
        self.path = path

    def emit(self, record: logging.LogRecord) -> None:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
