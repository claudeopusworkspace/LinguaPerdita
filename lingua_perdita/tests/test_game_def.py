"""Tests for game definition — validates against the engine."""

from idleengine import GameRuntime

from lingua_perdita.constants import ROOT_COUNT, TEXT_COUNT, TOOLS, UPGRADES
from lingua_perdita.game_def import build_definition
from lingua_perdita.language import generate_language


def _make_runtime():
    language = generate_language()
    definition = build_definition(language)
    return GameRuntime(definition), language, definition


def test_definition_validates():
    """GameDefinition passes engine validation."""
    language = generate_language()
    definition = build_definition(language)
    errors = definition.validate()
    assert errors == [], f"Validation errors: {errors}"


def test_runtime_creates():
    """GameRuntime initializes without error."""
    runtime, _, _ = _make_runtime()
    assert runtime is not None


def test_currency_exists():
    """Insight currency is defined."""
    runtime, _, _ = _make_runtime()
    assert runtime.state.currency_value("insight") == 0.0


def test_click_works():
    """Clicking produces insight."""
    runtime, _, _ = _make_runtime()
    amount = runtime.process_click("insight")
    assert amount > 0
    assert runtime.state.currency_value("insight") > 0


def test_tools_count():
    """All tools are defined."""
    _, _, definition = _make_runtime()
    tool_elements = [e for e in definition.elements if "tool" in e.tags]
    assert len(tool_elements) == len(TOOLS)


def test_upgrade_count():
    """All upgrades are defined."""
    _, _, definition = _make_runtime()
    upgrade_elements = [e for e in definition.elements if "upgrade" in e.tags]
    assert len(upgrade_elements) == len(UPGRADES)


def test_word_elements():
    """All words are defined as elements."""
    runtime, language, definition = _make_runtime()
    word_elements = [e for e in definition.elements if "word" in e.tags]
    assert len(word_elements) == len(language.words)

    # Each word element has max_count=1
    for e in word_elements:
        assert e.max_count == 1


def test_text_elements():
    """All texts are defined as elements."""
    _, _, definition = _make_runtime()
    text_elements = [e for e in definition.elements if "text" in e.tags]
    assert len(text_elements) == TEXT_COUNT


def test_root_discount_elements():
    """Root discount elements exist."""
    _, _, definition = _make_runtime()
    root_elements = [e for e in definition.elements if "root_bonus" in e.tags]
    assert len(root_elements) == ROOT_COUNT


def test_milestones():
    """Expected milestones are defined."""
    _, _, definition = _make_runtime()
    milestone_ids = {m.id for m in definition.milestones}

    assert "first_word" in milestone_ids
    assert "first_text_complete" in milestone_ids
    assert "all_words" in milestone_ids

    root_milestones = {m for m in milestone_ids if m.startswith("root_")}
    assert len(root_milestones) == ROOT_COUNT


def test_purchase_word():
    """Can purchase a cheap word when we have enough insight."""
    runtime, language, _ = _make_runtime()

    # Give ourselves enough insight for the cheapest word
    runtime.state.currencies["insight"].current = 500.0

    # Buy the cheapest word
    cheapest = language.word_list[0]
    result = runtime.try_purchase(cheapest.id)
    assert result is True
    assert runtime.state.element_count(cheapest.id) == 1


def test_purchase_tool():
    """Can purchase a tool and it produces insight."""
    runtime, _, _ = _make_runtime()

    # Give enough insight for a worn dictionary
    runtime.state.currencies["insight"].current = 500.0

    result = runtime.try_purchase("worn_dictionary")
    assert result is True
    assert runtime.state.element_count("worn_dictionary") == 1

    # Tick and check production
    runtime.tick(1.0)
    assert runtime.state.currency_rate("insight") > 0


def test_text_provides_production():
    """A text element with translated words produces insight."""
    runtime, language, _ = _make_runtime()

    # Buy the first text (free)
    first_text = language.text_list[0]
    result = runtime.try_purchase(first_text.id)
    assert result is True

    # No words translated yet — should produce 0
    runtime.tick(1.0)
    rate_before = runtime.state.currency_rate("insight")

    # Translate a word that's in this text
    word_id = first_text.word_ids[0]
    runtime.state.currencies["insight"].current = 100000.0
    runtime.try_purchase(word_id)

    # Now tick — rate should increase
    runtime.tick(1.0)
    rate_after = runtime.state.currency_rate("insight")
    assert rate_after > rate_before


def test_root_discovery_grants_discount():
    """Translating enough root words triggers root milestone and discount."""
    runtime, language, _ = _make_runtime()
    runtime.state.currencies["insight"].current = 1_000_000.0

    root = language.root_list[0]
    discount_id = f"discount_{root.id}"

    # Buy enough words to trigger root discovery
    for wid in root.word_ids[:root.discovery_threshold]:
        runtime.try_purchase(wid)

    # Tick to let milestone fire
    runtime.tick(0.1)

    # Discount element should be granted
    assert runtime.state.element_count(discount_id) == 1


def test_text_efficiency_upgrade():
    """Contextual Analysis upgrade increases text production."""
    runtime, language, _ = _make_runtime()
    runtime.state.currencies["insight"].current = 1_000_000.0

    # Buy first text and translate a word in it
    first_text = language.text_list[0]
    runtime.try_purchase(first_text.id)
    runtime.try_purchase(first_text.word_ids[0])
    runtime.tick(1.0)
    rate_before = runtime.state.currency_rate("insight")

    # Buy the text efficiency upgrade
    runtime.try_purchase("upg_text_efficiency")
    runtime.tick(1.0)
    rate_after = runtime.state.currency_rate("insight")

    assert rate_after > rate_before, (
        f"Text efficiency upgrade should increase rate: {rate_before} -> {rate_after}"
    )


def test_word_knowledge_bonus():
    """Word knowledge bonus gives passive Insight per translated word."""
    runtime, language, _ = _make_runtime()
    runtime.state.currencies["insight"].current = 1_000_000.0

    # Grant the hidden bonus element
    es = runtime.state.elements.get("word_knowledge_bonus")
    assert es is not None, "word_knowledge_bonus element missing"
    es.count = 1

    # No words translated yet
    runtime.tick(1.0)
    rate_zero = runtime.state.currency_rate("insight")

    # Translate a word
    runtime.try_purchase(language.word_list[0].id)
    runtime.tick(1.0)
    rate_one = runtime.state.currency_rate("insight")

    assert rate_one > rate_zero, (
        f"Translating a word should increase rate via knowledge bonus: {rate_zero} -> {rate_one}"
    )
