from pathlib import Path

from voice_control_pc.config import load_config_bundle
from voice_control_pc.nlu import RuleBasedNLU


def build_nlu() -> RuleBasedNLU:
    project_root = Path(__file__).resolve().parents[1]
    config = load_config_bundle(project_root)
    return RuleBasedNLU(
        commands=config.commands,
        apps=config.apps,
        min_confidence=config.settings.nlu.min_confidence,
    )


def test_match_open_app() -> None:
    nlu = build_nlu()
    match = nlu.match("Открой браузер")
    assert match.intent == "open_app"
    assert match.slots["app_name"] == "браузер"


def test_match_open_folder() -> None:
    nlu = build_nlu()
    match = nlu.match("открой папку загрузки")
    assert match.intent == "open_folder"
    assert match.slots["folder_name"] == "загрузки"


def test_unknown_command() -> None:
    nlu = build_nlu()
    match = nlu.match("расскажи смешную историю")
    assert match.intent is None
