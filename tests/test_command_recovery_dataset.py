from pathlib import Path

from voice_control_pc.config import load_config_bundle
from voice_control_pc.ml.command_recovery import build_canonical_texts_from_commands


def test_build_canonical_mapping() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config = load_config_bundle(project_root)
    mapping = build_canonical_texts_from_commands(config.commands)

    assert "open_folder" in mapping
    assert any("загрузки" in example for example in mapping["open_folder"])
