from pathlib import Path

from voice_control_pc.config import load_config_bundle
from voice_control_pc.service import VoiceControlService


def test_process_text_command_dry_run() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config = load_config_bundle(project_root)
    service = VoiceControlService(config=config, dry_run=True)

    match, result = service.process_text_command("открой браузер")

    assert match["intent"] == "open_app"
    assert result.success is True
    assert result.status == "dry_run"


def test_confirmation_required() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config = load_config_bundle(project_root)
    service = VoiceControlService(config=config, dry_run=True)

    match, result = service.process_text_command("выключи компьютер")

    assert match["intent"] == "shutdown_pc"
    assert result.status == "confirmation_required"
