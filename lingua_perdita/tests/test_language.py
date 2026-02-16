"""Tests for language model generation."""

from lingua_perdita.constants import (
    ROOT_COUNT,
    ROOT_DISCOVERY_THRESHOLD,
    TEXT_COUNT,
    WORDS_PER_CATEGORY,
    WORDS_PER_ROOT,
)
from lingua_perdita.language import generate_language


def test_determinism():
    """Same seed produces identical language models."""
    a = generate_language(seed=42)
    b = generate_language(seed=42)

    assert len(a.words) == len(b.words)
    for wid in a.words:
        assert a.words[wid] == b.words[wid]

    assert len(a.roots) == len(b.roots)
    for rid in a.roots:
        assert a.roots[rid] == b.roots[rid]

    assert len(a.texts) == len(b.texts)
    for tid in a.texts:
        assert a.texts[tid] == b.texts[tid]


def test_different_seeds():
    """Different seeds produce different languages."""
    a = generate_language(seed=1)
    b = generate_language(seed=2)

    # Word order should differ
    a_order = [w.id for w in a.word_list]
    b_order = [w.id for w in b.word_list]
    # They could theoretically be the same but extremely unlikely
    assert a_order != b_order or a.word_list[0].meaning != b.word_list[0].meaning


def test_word_count():
    """Total word count matches constants."""
    model = generate_language()
    expected = sum(WORDS_PER_CATEGORY.values())
    assert len(model.words) == expected
    assert len(model.word_list) == expected


def test_word_categories():
    """Each category has the right number of words."""
    model = generate_language()
    counts: dict[str, int] = {}
    for w in model.word_list:
        counts[w.category] = counts.get(w.category, 0) + 1

    for cat, expected in WORDS_PER_CATEGORY.items():
        assert counts.get(cat, 0) == expected, f"{cat}: expected {expected}, got {counts.get(cat, 0)}"


def test_root_structure():
    """Roots have correct count and word assignments."""
    model = generate_language()
    assert len(model.roots) == ROOT_COUNT

    for root in model.root_list:
        assert len(root.word_ids) == WORDS_PER_ROOT
        assert root.discovery_threshold == ROOT_DISCOVERY_THRESHOLD
        for wid in root.word_ids:
            assert wid in model.words
            assert model.words[wid].root_id == root.id


def test_all_words_have_roots():
    """Every word is assigned to a root."""
    model = generate_language()
    for w in model.word_list:
        assert w.root_id, f"Word {w.id} has no root"
        assert w.root_id in model.roots


def test_text_structure():
    """Texts have correct count and valid word references."""
    model = generate_language()
    assert len(model.texts) == TEXT_COUNT

    for text in model.text_list:
        assert len(text.word_ids) >= 8
        assert len(text.word_ids) <= 12
        for wid in text.word_ids:
            assert wid in model.words, f"Text {text.id} references unknown word {wid}"


def test_word_costs_increase():
    """Words are sorted by cost (cheapest first)."""
    model = generate_language()
    costs = [w.base_cost for w in model.word_list]
    assert costs == sorted(costs)


def test_glyph_indices_valid():
    """All glyph indices are within alphabet bounds."""
    model = generate_language()
    for w in model.word_list:
        assert len(w.glyph_indices) >= 1
        for idx in w.glyph_indices:
            assert 0 <= idx < 26


def test_words_for_root():
    """words_for_root returns correct words."""
    model = generate_language()
    for root in model.root_list:
        words = model.words_for_root(root.id)
        assert len(words) == WORDS_PER_ROOT
        for w in words:
            assert w.root_id == root.id


def test_unique_words_in_text():
    """unique_words_in_text returns deduplicated words."""
    model = generate_language()
    for text in model.text_list:
        unique = model.unique_words_in_text(text.id)
        ids = [w.id for w in unique]
        assert len(ids) == len(set(ids))
        # Every unique word should appear in the text
        for w in unique:
            assert w.id in text.word_ids


def test_text_unlock_thresholds():
    """Texts have increasing unlock thresholds."""
    model = generate_language()
    thresholds = [t.unlock_threshold for t in model.text_list]
    assert thresholds == sorted(thresholds)
    # First text should be free (threshold 0)
    assert thresholds[0] == 0


def test_unique_meanings():
    """No two words share the same English meaning."""
    model = generate_language()
    meanings = [w.meaning for w in model.word_list]
    assert len(meanings) == len(set(meanings)), f"Duplicate meanings: {[m for m in meanings if meanings.count(m) > 1]}"


def test_unique_glyph_sequences():
    """No two words share the same glyph sequence."""
    model = generate_language()
    sequences = [w.glyph_indices for w in model.word_list]
    assert len(sequences) == len(set(sequences)), "Duplicate glyph sequences found"


def test_unique_across_seeds():
    """Uniqueness guarantees hold across multiple seeds."""
    for seed in [1, 42, 99, 123, 777]:
        model = generate_language(seed=seed)
        meanings = [w.meaning for w in model.word_list]
        assert len(meanings) == len(set(meanings)), f"Seed {seed}: duplicate meanings"
        sequences = [w.glyph_indices for w in model.word_list]
        assert len(sequences) == len(set(sequences)), f"Seed {seed}: duplicate glyphs"


def test_glyph_length_ranges():
    """Words have glyph counts matching their category range."""
    from lingua_perdita.constants import GLYPHS_PER_WORD
    model = generate_language()
    for w in model.word_list:
        lo, hi = GLYPHS_PER_WORD[w.category]
        assert lo <= len(w.glyph_indices) <= hi, (
            f"{w.id} ({w.category}): {len(w.glyph_indices)} glyphs, expected {lo}-{hi}"
        )
