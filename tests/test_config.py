from pathlib import Path

from voice_control_pc.config import load_config_bundle


def test_load_config_bundle() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config = load_config_bundle(project_root)

    assert config.settings.app.locale == "ru-RU"
    assert len(config.commands.intents) >= 5
    assert "браузер" in config.apps.applications
