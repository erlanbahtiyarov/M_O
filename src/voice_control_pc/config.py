"""Configuration loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from voice_control_pc.models import AppsCatalog, CommandCatalog, ResolvedConfig, Settings


def load_yaml_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        payload = yaml.safe_load(fh) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")
    return payload


def resolve_project_root(explicit_root: Path | None = None) -> Path:
    if explicit_root:
        return explicit_root.resolve()
    return Path(__file__).resolve().parents[2]


def load_config_bundle(project_root: Path | None = None) -> ResolvedConfig:
    root = resolve_project_root(project_root)
    config_dir = root / "configs"

    settings = Settings.model_validate(load_yaml_file(config_dir / "default.yaml"))
    commands = CommandCatalog.model_validate(load_yaml_file(config_dir / "commands.yaml"))
    apps = AppsCatalog.model_validate(load_yaml_file(config_dir / "apps.yaml"))

    return ResolvedConfig(
        settings=settings,
        commands=commands,
        apps=apps,
        project_root=root,
    )
