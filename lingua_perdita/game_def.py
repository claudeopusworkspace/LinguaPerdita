"""Translate a LanguageModel into an IdleGameEngine GameDefinition.

This is the bridge between the procedural language and the idle game engine.
"""

from __future__ import annotations

from idleengine import (
    ClickTarget,
    CostScaling,
    CurrencyDef,
    Effect,
    EffectDef,
    EffectType,
    ElementDef,
    GameConfig,
    GameDefinition,
    GameState,
    MilestoneDef,
    Req,
)

from lingua_perdita.constants import (
    CLICK_BASE_VALUE,
    INSIGHT_PER_TRANSLATED_WORD,
    ROOT_COST_MULTIPLIER,
    TEXT_EFFICIENCY_MULT,
    TOOLS,
    UPGRADES,
    WORD_BASE_INSIGHT_RATE,
)
from lingua_perdita.language import LanguageModel


def _total_words_translated(state: GameState, language: LanguageModel) -> int:
    """Count how many words the player has translated."""
    return sum(
        1 for w in language.word_list
        if state.element_count(w.id) >= 1
    )


def _words_translated_in_root(
    state: GameState, language: LanguageModel, root_id: str,
) -> int:
    """Count translated words belonging to a specific root."""
    root = language.roots[root_id]
    return sum(
        1 for wid in root.word_ids
        if state.element_count(wid) >= 1
    )


def build_definition(language: LanguageModel) -> GameDefinition:
    """Build a complete GameDefinition from a LanguageModel."""

    currencies = [
        CurrencyDef(id="insight", display_name="Insight", initial_value=0.0),
    ]

    elements: list[ElementDef] = []
    milestones: list[MilestoneDef] = []

    # ── Tools (repeatable generators) ────────────────────────────────
    for tool in TOOLS:
        elements.append(ElementDef(
            id=tool["id"],
            display_name=tool["name"],
            description=f"+{tool['rate']} Insight/s each",
            base_cost={"insight": float(tool["base_cost"])},
            cost_scaling=CostScaling.exponential(tool["scaling"]),
            effects=[
                Effect.per_count(
                    tool["id"],
                    EffectType.PRODUCTION_FLAT,
                    "insight",
                    tool["rate"],
                ),
            ],
            category="tool",
            tags={"tool"},
        ))

    # ── One-time upgrades ────────────────────────────────────────────
    for upg in UPGRADES:
        etype = upg["effect_type"]
        effects: list[EffectDef] = []

        if etype == "CLICK_FLAT":
            effects.append(
                Effect.static(EffectType.CLICK_FLAT, "insight", upg["effect_value"])
            )
        elif etype == "CLICK_MULT":
            effects.append(
                Effect.static(EffectType.CLICK_MULT, "insight", upg["effect_value"])
            )
        elif etype == "PRODUCTION_ADD_PCT":
            effects.append(
                Effect.static(EffectType.PRODUCTION_ADD_PCT, "insight", upg["effect_value"])
            )
        elif etype == "TEXT_EFFICIENCY":
            # Text efficiency is handled via the text elements' DynamicFloat
            # We store it as a tag marker — the text effect lambdas check this
            pass

        elements.append(ElementDef(
            id=upg["id"],
            display_name=upg["name"],
            description=upg["description"],
            base_cost={"insight": float(upg["cost"])},
            max_count=1,
            effects=effects,
            category="upgrade",
            tags={"upgrade"},
        ))

    # ── Words (one-time purchases) ───────────────────────────────────
    for word in language.word_list:
        elements.append(ElementDef(
            id=word.id,
            display_name=word.meaning.title(),
            description=f"Translate '{word.meaning}'",
            base_cost={"insight": float(word.base_cost)},
            max_count=1,
            category="word",
            tags={"word", f"root:{word.root_id}", f"cat:{word.category}"},
        ))

    # ── Root discount elements (hidden, granted by milestones) ───────
    for root in language.root_list:
        discount_effects: list[EffectDef] = []
        for wid in root.word_ids:
            discount_effects.append(
                Effect.static(EffectType.COST_MULT, wid, ROOT_COST_MULTIPLIER)
            )

        elements.append(ElementDef(
            id=f"discount_{root.id}",
            display_name=f"Root: {root.display_name}",
            description=f"Discovered root '{root.display_name}' — related words cost less",
            base_cost={},  # free, granted by milestone
            max_count=1,
            effects=discount_effects,
            requirements=[Req.custom(lambda s: False)],  # never purchasable directly
            category="root_bonus",
            tags={"root_bonus", "hidden"},
        ))

    # ── Texts (one-time, provide passive income) ─────────────────────
    for text in language.text_list:
        text_word_ids = list(text.word_ids)
        text_id = text.id
        lang = language  # capture for closure

        def _make_text_effect(t_word_ids: list[str], lang_ref: LanguageModel) -> EffectDef:
            """Create a DynamicFloat PRODUCTION_FLAT effect for a text."""
            def _value(state: GameState) -> float:
                translated = sum(
                    1 for wid in t_word_ids
                    if state.element_count(wid) >= 1
                )
                base_rate = translated * INSIGHT_PER_TRANSLATED_WORD
                # Check text efficiency upgrade
                if state.element_count("upg_text_efficiency") >= 1:
                    return base_rate * TEXT_EFFICIENCY_MULT
                return base_rate

            return EffectDef(
                type=EffectType.PRODUCTION_FLAT,
                target="insight",
                value=_value,
            )

        # First text is free, others gated by total words translated
        reqs = []
        if text.unlock_threshold > 0:
            threshold = text.unlock_threshold
            lang_ref = language

            def _make_unlock_req(thresh: int, lr: LanguageModel):
                return Req.custom(lambda s, t=thresh, l=lr: _total_words_translated(s, l) >= t)

            reqs.append(_make_unlock_req(threshold, lang_ref))

        elements.append(ElementDef(
            id=text.id,
            display_name=text.display_name,
            description=f"Study this text for passive Insight",
            base_cost={} if text.unlock_threshold == 0 else {"insight": 0.0},
            max_count=1,
            effects=[_make_text_effect(text_word_ids, language)],
            requirements=reqs,
            category="text",
            tags={"text"},
        ))

    # ── Word knowledge bonus (hidden, auto-purchased) ───────────────
    def _word_knowledge_value(state: GameState, lang=language) -> float:
        """Passive Insight/s based on total translated words."""
        count = sum(1 for w in lang.word_list if state.element_count(w.id) >= 1)
        return count * WORD_BASE_INSIGHT_RATE

    elements.append(ElementDef(
        id="word_knowledge_bonus",
        display_name="Word Knowledge",
        description="Passive Insight from translated words",
        base_cost={},
        max_count=1,
        effects=[EffectDef(
            type=EffectType.PRODUCTION_FLAT,
            target="insight",
            value=_word_knowledge_value,
        )],
        requirements=[Req.custom(lambda s: False)],  # never purchasable directly
        category="bonus",
        tags={"bonus", "hidden"},
    ))

    # ── Milestones ───────────────────────────────────────────────────

    # first_word: any word translated
    milestones.append(MilestoneDef(
        id="first_word",
        description="Translated your first word",
        trigger=Req.custom(
            lambda s, l=language: _total_words_translated(s, l) >= 1
        ),
    ))

    # Root discoveries
    for root in language.root_list:
        root_id = root.id
        threshold = root.discovery_threshold
        discount_id = f"discount_{root_id}"

        def _make_root_trigger(rid: str, thresh: int, disc_id: str, lr: LanguageModel):
            return Req.custom(
                lambda s, r=rid, t=thresh, l=lr: _words_translated_in_root(s, l, r) >= t
            )

        def _make_root_callback(disc_id_inner: str):
            def _grant_discount(state: GameState) -> None:
                es = state.elements.get(disc_id_inner)
                if es is not None and es.count == 0:
                    es.count = 1
            return _grant_discount

        milestones.append(MilestoneDef(
            id=f"root_{root_id}",
            description=f"Discovered root '{root.display_name}'",
            trigger=_make_root_trigger(root_id, threshold, discount_id, language),
            on_trigger=_make_root_callback(discount_id),
        ))

    # first_text_complete: all words in text 0 translated
    first_text = language.text_list[0]
    first_text_word_ids = list(set(first_text.word_ids))

    milestones.append(MilestoneDef(
        id="first_text_complete",
        description=f"Completed '{first_text.display_name}'",
        trigger=Req.custom(
            lambda s, wids=first_text_word_ids: all(
                s.element_count(wid) >= 1 for wid in wids
            )
        ),
    ))

    # all_words: all 30 words translated
    all_word_ids = [w.id for w in language.word_list]
    milestones.append(MilestoneDef(
        id="all_words",
        description="Translated all words",
        trigger=Req.custom(
            lambda s, wids=all_word_ids: all(
                s.element_count(wid) >= 1 for wid in wids
            )
        ),
    ))

    return GameDefinition(
        config=GameConfig(name="Lingua Perdita", tick_rate=10),
        currencies=currencies,
        elements=elements,
        milestones=milestones,
        click_targets=[ClickTarget(currency="insight", base_value=CLICK_BASE_VALUE)],
    )
