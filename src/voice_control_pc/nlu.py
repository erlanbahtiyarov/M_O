"""Rule-based NLU for Russian desktop commands."""

from __future__ import annotations

import re
from collections.abc import Iterable

from voice_control_pc.models import AppsCatalog, CommandCatalog, CommandSpec, IntentMatch


def normalize_text(text: str) -> str:
    normalized = text.lower().replace("ё", "е").strip()
    normalized = re.sub(r"[^\w\s-]", " ", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def token_overlap_score(left: str, right: str) -> float:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return intersection / union


class RuleBasedNLU:
    def __init__(self, commands: CommandCatalog, apps: AppsCatalog, min_confidence: float = 0.7):
        self.commands = commands
        self.apps = apps
        self.min_confidence = min_confidence

    def match(self, text: str) -> IntentMatch:
        normalized_text = normalize_text(text)
        best_spec: CommandSpec | None = None
        best_example: str | None = None
        best_score = 0.0

        for spec in self.commands.intents:
            for example in spec.examples:
                normalized_example = normalize_text(example)
                score = self._score(normalized_text, normalized_example)
                if score > best_score:
                    best_score = score
                    best_spec = spec
                    best_example = example

        if not best_spec or best_score < self.min_confidence:
            return IntentMatch(
                text=text,
                normalized_text=normalized_text,
                intent=None,
                action=None,
                confidence=best_score,
                slots={},
                dangerous=False,
                matched_example=best_example,
            )

        slots = self._extract_slots(best_spec.intent, normalized_text)
        return IntentMatch(
            text=text,
            normalized_text=normalized_text,
            intent=best_spec.intent,
            action=best_spec.action,
            confidence=best_score,
            slots=slots,
            dangerous=best_spec.dangerous,
            matched_example=best_example,
        )

    def _score(self, normalized_text: str, normalized_example: str) -> float:
        if normalized_text == normalized_example:
            return 1.0
        if normalized_text.startswith(normalized_example) or normalized_example.startswith(
            normalized_text
        ):
            return 0.92
        return token_overlap_score(normalized_text, normalized_example)

    def _extract_slots(self, intent: str, normalized_text: str) -> dict[str, str]:
        slots: dict[str, str] = {}
        if intent == "open_app":
            app_name = self._find_alias(normalized_text, self._iter_app_aliases())
            if app_name:
                slots["app_name"] = app_name
        elif intent == "open_folder":
            folder_name = self._find_alias(normalized_text, self._iter_folder_aliases())
            if folder_name:
                slots["folder_name"] = folder_name
        elif intent == "take_screenshot":
            if "главного экрана" in normalized_text:
                slots["screen_area"] = "главного экрана"
            elif "экрана" in normalized_text:
                slots["screen_area"] = "экрана"
        return slots

    def _iter_app_aliases(self) -> Iterable[tuple[str, str]]:
        for canonical_name, entry in self.apps.applications.items():
            for alias in entry.aliases:
                yield normalize_text(alias), canonical_name

    def _iter_folder_aliases(self) -> Iterable[tuple[str, str]]:
        for canonical_name, entry in self.apps.folders.items():
            for alias in entry.aliases:
                yield normalize_text(alias), canonical_name

    def _find_alias(self, normalized_text: str, aliases: Iterable[tuple[str, str]]) -> str | None:
        best_name: str | None = None
        best_length = -1
        for alias, canonical_name in aliases:
            if alias in normalized_text and len(alias) > best_length:
                best_name = canonical_name
                best_length = len(alias)
        return best_name
