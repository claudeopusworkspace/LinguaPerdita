"""Presenter — wraps GameRuntime + LanguageModel for UI queries.

The presenter is the only bridge between UI and engine.
All game-specific queries go through here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from idleengine import (
    ElementDef,
    ElementStatus,
    GameRuntime,
    PrestigeResult,
)

from lingua_perdita.constants import TOOLS, UPGRADES
from lingua_perdita.game_def import build_definition
from lingua_perdita.language import LanguageModel, Root, Text, Word, generate_language

if TYPE_CHECKING:
    from idleengine import GameState


# Pre-built effect descriptions for display
EFFECT_TEXT: dict[str, str] = {}
for _tool in TOOLS:
    EFFECT_TEXT[_tool["id"]] = f"+{_tool['rate']} Insight/s each"
for _upg in UPGRADES:
    EFFECT_TEXT[_upg["id"]] = _upg["description"]


class GamePresenter:
    """Wraps GameRuntime and provides UI-friendly queries."""

    def __init__(self, language: LanguageModel | None = None, seed: int = 42):
        if language is None:
            language = generate_language(seed)
        self.language = language
        self.definition = build_definition(language)
        self.runtime = GameRuntime(self.definition)

        self._milestones_seen: set[str] = set()
        self._new_milestones: list[str] = []
        self._notifications: list[str] = []

        # Auto-unlock the first text (free, no cost)
        first_text = language.text_list[0]
        if self.state.element_count(first_text.id) == 0:
            self.runtime.try_purchase(first_text.id)

    @property
    def state(self) -> GameState:
        return self.runtime.get_state()

    # ── Core actions ─────────────────────────────────────────────────

    def tick(self, delta: float) -> None:
        """Advance game time and check for new milestones."""
        self.runtime.tick(delta)
        self._auto_unlock_texts()
        self._check_new_milestones()

    def _auto_unlock_texts(self) -> None:
        """Auto-purchase texts whose requirements are met (they cost 0)."""
        for text in self.language.text_list:
            if self.state.element_count(text.id) == 0:
                self.runtime.try_purchase(text.id)

    def process_click(self) -> float:
        """Process a player click on the tablet. Returns Insight earned."""
        return self.runtime.process_click("insight")

    def try_purchase(self, element_id: str) -> bool:
        """Attempt to purchase an element. Returns success."""
        return self.runtime.try_purchase(element_id)

    # ── Word/Root/Text queries ───────────────────────────────────────

    def is_word_translated(self, word_id: str) -> bool:
        return self.state.element_count(word_id) >= 1

    def total_words_translated(self) -> int:
        return sum(
            1 for w in self.language.word_list
            if self.is_word_translated(w.id)
        )

    def words_translated_in_root(self, root_id: str) -> int:
        root = self.language.roots[root_id]
        return sum(
            1 for wid in root.word_ids
            if self.state.element_count(wid) >= 1
        )

    def is_root_discovered(self, root_id: str) -> bool:
        return self.state.has_milestone(f"root_{root_id}")

    def is_text_unlocked(self, text_id: str) -> bool:
        """Check if a text is unlocked (purchased or available)."""
        return self.state.element_count(text_id) >= 1

    def is_text_available(self, text_id: str) -> bool:
        """Check if a text is available for purchase."""
        status = self._get_element_status(text_id)
        return status is not None and status.available

    def text_translated_count(self, text_id: str) -> int:
        """How many unique words in this text are translated."""
        text = self.language.texts[text_id]
        unique_ids = set(text.word_ids)
        return sum(1 for wid in unique_ids if self.is_word_translated(wid))

    def text_total_unique_words(self, text_id: str) -> int:
        """Total unique words in this text."""
        text = self.language.texts[text_id]
        return len(set(text.word_ids))

    # ── Shop queries ─────────────────────────────────────────────────

    def get_tools(self) -> list[tuple[ElementDef, ElementStatus | None]]:
        """Return tool elements with their status."""
        available = {e.id: e for e in self.runtime.get_available_purchases()}
        result = []
        for edef in self.definition.elements:
            if edef.category == "tool":
                result.append((edef, available.get(edef.id)))
        return result

    def get_upgrades(self) -> list[tuple[ElementDef, ElementStatus | None]]:
        """Return upgrade elements (showing purchased and available)."""
        available = {e.id: e for e in self.runtime.get_available_purchases()}
        result = []
        for edef in self.definition.elements:
            if edef.category == "upgrade":
                status = available.get(edef.id)
                count = self.state.element_count(edef.id)
                if status is not None or count > 0:
                    result.append((edef, status))
        return result

    def get_purchasable_words(self) -> list[tuple[Word, ElementStatus | None]]:
        """Return words available for purchase, sorted by cost."""
        available = {e.id: e for e in self.runtime.get_available_purchases()}
        result = []
        for word in self.language.word_list:
            if not self.is_word_translated(word.id):
                result.append((word, available.get(word.id)))
        return result

    def get_word_cost(self, word_id: str) -> float:
        """Get current cost of a word (may be discounted by root discovery)."""
        cost = self.runtime.compute_current_cost(word_id)
        return cost.get("insight", 0.0)

    def get_effect_summary(self, element_id: str) -> str:
        """Return human-readable effect text for an element."""
        return EFFECT_TEXT.get(element_id, "")

    # ── Currency queries ─────────────────────────────────────────────

    def insight_value(self) -> float:
        return self.state.currency_value("insight")

    def insight_rate(self) -> float:
        return self.state.currency_rate("insight")

    # ── Milestone notifications ──────────────────────────────────────

    def pop_new_milestones(self) -> list[str]:
        """Return and clear newly reached milestones."""
        milestones = list(self._new_milestones)
        self._new_milestones.clear()
        return milestones

    def _check_new_milestones(self) -> None:
        for mid in self.state.milestones_reached:
            if mid not in self._milestones_seen:
                self._milestones_seen.add(mid)
                self._new_milestones.append(mid)

    def get_milestone_text(self, milestone_id: str) -> str:
        """Get display text for a milestone."""
        mdef = self.definition.get_milestone(milestone_id)
        if mdef:
            return mdef.description
        return milestone_id

    # ── State restoration ────────────────────────────────────────────

    def restore_milestones_seen(self) -> None:
        """After loading, mark existing milestones as seen."""
        for mid in self.state.milestones_reached:
            self._milestones_seen.add(mid)

    # ── Helpers ──────────────────────────────────────────────────────

    def _get_element_status(self, element_id: str) -> ElementStatus | None:
        available = {e.id: e for e in self.runtime.get_available_purchases()}
        return available.get(element_id)
