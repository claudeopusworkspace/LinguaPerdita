"""Procedural language generation — pure data layer, no engine dependency.

Generates Words, Roots, Texts, and a complete LanguageModel from a seed.
All generation is deterministic: same seed → same language.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from lingua_perdita.constants import (
    ALPHABET_SIZE,
    DEFAULT_SEED,
    GLYPHS_PER_WORD,
    ROOT_COUNT,
    ROOT_DISCOVERY_THRESHOLD,
    TEXT_COUNT,
    TEXT_UNLOCK_THRESHOLDS,
    TEXT_WORD_SLOTS_RANGE,
    WORD_COST_RANGES,
    WORDS_PER_CATEGORY,
    WORDS_PER_ROOT,
)

# ── Meaning pools (English translations) ─────────────────────────────

_MEANINGS = {
    "common": [
        "water", "fire", "earth", "sky", "stone", "hand", "eye", "sun",
        "moon", "star", "tree", "river", "path", "door", "light",
        "bone", "wind", "seed", "salt", "ash",
    ],
    "everyday": [
        "gather", "build", "speak", "listen", "travel", "carry", "break",
        "mend", "trade", "plant", "harvest", "shelter", "guard", "rest",
        "weave", "forge", "carve", "kindle", "bind", "honor",
    ],
    "academic": [
        "knowledge", "theorem", "axiom", "paradox", "chronicle", "alchemy",
        "cipher", "cosmology", "dialectic", "epitome", "schema", "paradigm",
    ],
    "rare": [
        "transcendence", "apotheosis", "eschatology", "pneuma", "anamnesis",
        "theurgy", "metempsychosis", "henosis",
    ],
}

_TEXT_NAMES = [
    "The Foundation Tablet",
    "The Builder's Record",
    "The Scholar's Codex",
    "The Hidden Archive",
]

_ROOT_NAMES = [
    "kel", "myr", "tho", "van", "zir",
    "arn", "dru", "fen", "gol", "hes",
]


@dataclass(frozen=True)
class Word:
    """A single word in the lost language."""
    id: str
    root_id: str
    glyph_indices: tuple[int, ...]  # indices into the 26-glyph alphabet
    meaning: str
    category: str
    base_cost: int


@dataclass(frozen=True)
class Root:
    """A morphological root shared by a family of words."""
    id: str
    display_name: str
    word_ids: tuple[str, ...]
    discovery_threshold: int = ROOT_DISCOVERY_THRESHOLD


@dataclass(frozen=True)
class Text:
    """A text composed of word slots (with possible repetition)."""
    id: str
    display_name: str
    word_ids: tuple[str, ...]  # ordered word slots, may repeat
    category: str
    unlock_threshold: int  # total words translated to unlock


@dataclass
class LanguageModel:
    """Complete generated language: words, roots, texts, alphabet config."""
    seed: int
    words: dict[str, Word] = field(default_factory=dict)
    roots: dict[str, Root] = field(default_factory=dict)
    texts: dict[str, Text] = field(default_factory=dict)

    # Ordered lists for stable iteration
    word_list: list[Word] = field(default_factory=list)
    root_list: list[Root] = field(default_factory=list)
    text_list: list[Text] = field(default_factory=list)

    def words_for_root(self, root_id: str) -> list[Word]:
        """Return all words belonging to a root."""
        root = self.roots[root_id]
        return [self.words[wid] for wid in root.word_ids]

    def unique_words_in_text(self, text_id: str) -> list[Word]:
        """Return unique words referenced by a text."""
        text = self.texts[text_id]
        seen: set[str] = set()
        result: list[Word] = []
        for wid in text.word_ids:
            if wid not in seen:
                seen.add(wid)
                result.append(self.words[wid])
        return result

    def texts_containing_word(self, word_id: str) -> list[Text]:
        """Return all texts that contain a given word."""
        return [t for t in self.text_list if word_id in t.word_ids]


def generate_language(seed: int = DEFAULT_SEED) -> LanguageModel:
    """Generate a complete LanguageModel from a seed. Deterministic."""
    rng = random.Random(seed)
    model = LanguageModel(seed=seed)

    # ── Generate words ───────────────────────────────────────────────
    all_words: list[Word] = []
    word_index = 0
    used_meanings: set[str] = set()
    used_glyphs: set[tuple[int, ...]] = set()

    for category, count in WORDS_PER_CATEGORY.items():
        meanings = list(_MEANINGS[category])
        rng.shuffle(meanings)
        cost_lo, cost_hi = WORD_COST_RANGES[category]
        glyph_lo, glyph_hi = GLYPHS_PER_WORD[category]

        # Pick unique meanings for this category
        unique_meanings: list[str] = []
        for m in meanings:
            if m not in used_meanings:
                unique_meanings.append(m)
            if len(unique_meanings) == count:
                break

        for i in range(count):
            meaning = unique_meanings[i]
            used_meanings.add(meaning)

            # Spread costs across the range
            if count > 1:
                t = i / (count - 1)
            else:
                t = 0.5
            base_cost = int(cost_lo + t * (cost_hi - cost_lo))

            # Generate unique glyph sequence
            glyph_count = rng.randint(glyph_lo, glyph_hi)
            for _attempt in range(100):
                glyph_indices = tuple(
                    rng.randint(0, ALPHABET_SIZE - 1)
                    for _ in range(glyph_count)
                )
                if glyph_indices not in used_glyphs:
                    break
            used_glyphs.add(glyph_indices)

            word = Word(
                id=f"word_{word_index:02d}",
                root_id="",  # assigned below
                glyph_indices=glyph_indices,
                meaning=meaning,
                category=category,
                base_cost=base_cost,
            )
            all_words.append(word)
            word_index += 1

    # Shuffle words before assigning to roots so roots aren't category-aligned
    rng.shuffle(all_words)

    # ── Assign words to roots ────────────────────────────────────────
    root_count = min(ROOT_COUNT, len(all_words) // WORDS_PER_ROOT)
    root_names = _ROOT_NAMES[:root_count]

    roots: list[Root] = []
    for ri in range(root_count):
        root_id = f"root_{ri:02d}"
        start = ri * WORDS_PER_ROOT
        end = start + WORDS_PER_ROOT
        root_word_ids: list[str] = []

        for wi in range(start, end):
            old = all_words[wi]
            # Replace with root_id assigned
            all_words[wi] = Word(
                id=old.id,
                root_id=root_id,
                glyph_indices=old.glyph_indices,
                meaning=old.meaning,
                category=old.category,
                base_cost=old.base_cost,
            )
            root_word_ids.append(old.id)

        roots.append(Root(
            id=root_id,
            display_name=root_names[ri],
            word_ids=tuple(root_word_ids),
        ))

    # Sort words by cost for stable ordering
    all_words.sort(key=lambda w: w.base_cost)

    # Populate model
    for w in all_words:
        model.words[w.id] = w
        model.word_list.append(w)

    for r in roots:
        model.roots[r.id] = r
        model.root_list.append(r)

    # ── Generate texts ───────────────────────────────────────────────
    text_names = _TEXT_NAMES[:TEXT_COUNT]
    text_categories = ["common", "everyday", "academic", "rare"]

    for ti in range(TEXT_COUNT):
        text_id = f"text_{ti:02d}"
        slot_count = rng.randint(*TEXT_WORD_SLOTS_RANGE)
        category = text_categories[ti % len(text_categories)]

        # Pick words for this text: bias toward the category but include others
        # First text uses 60% bias; later texts use 40% for better word coverage
        bias = 0.6 if ti == 0 else 0.4
        category_words = [w for w in all_words if w.category == category]
        other_words = [w for w in all_words if w.category != category]

        text_word_ids: list[str] = []
        for si in range(slot_count):
            if category_words and (rng.random() < bias or not other_words):
                w = rng.choice(category_words)
            else:
                w = rng.choice(other_words) if other_words else rng.choice(all_words)
            text_word_ids.append(w.id)

        unlock = TEXT_UNLOCK_THRESHOLDS[ti] if ti < len(TEXT_UNLOCK_THRESHOLDS) else ti * 8

        text = Text(
            id=text_id,
            display_name=text_names[ti] if ti < len(text_names) else f"Text {ti + 1}",
            word_ids=tuple(text_word_ids),
            category=category,
            unlock_threshold=unlock,
        )
        model.texts[text_id] = text
        model.text_list.append(text)

    # ── Ensure all words appear in at least one text ──────────────
    all_word_ids_in_texts: set[str] = set()
    for text in model.text_list:
        all_word_ids_in_texts.update(text.word_ids)

    orphaned = [w.id for w in all_words if w.id not in all_word_ids_in_texts]
    if orphaned:
        rng.shuffle(orphaned)
        remaining = list(orphaned)

        # Pass 1: replace within-text duplicates
        for ti, text in enumerate(model.text_list):
            if not remaining:
                break
            word_counts: dict[str, list[int]] = {}
            for idx, wid in enumerate(text.word_ids):
                word_counts.setdefault(wid, []).append(idx)

            replaceable = []
            for wid, indices in word_counts.items():
                if len(indices) > 1:
                    replaceable.extend(indices[1:])

            word_ids = list(text.word_ids)
            for slot_idx in replaceable:
                if not remaining:
                    break
                word_ids[slot_idx] = remaining.pop()
            _update_text(model, ti, text, tuple(word_ids))

        # Pass 2: replace cross-text duplicates (words in multiple texts)
        if remaining:
            # Count how many texts each word appears in
            word_text_count: dict[str, int] = {}
            for text in model.text_list:
                for wid in set(text.word_ids):
                    word_text_count[wid] = word_text_count.get(wid, 0) + 1

            for ti, text in enumerate(model.text_list):
                if not remaining:
                    break
                word_ids = list(text.word_ids)
                for slot_idx, wid in enumerate(word_ids):
                    if not remaining:
                        break
                    if word_text_count.get(wid, 0) > 1:
                        orphan_wid = remaining.pop()
                        word_text_count[wid] -= 1
                        word_text_count[orphan_wid] = word_text_count.get(orphan_wid, 0) + 1
                        word_ids[slot_idx] = orphan_wid
                _update_text(model, ti, text, tuple(word_ids))

    return model


def _update_text(
    model: LanguageModel, idx: int, old_text: Text, new_word_ids: tuple[str, ...],
) -> None:
    """Replace a text in the model with updated word_ids."""
    if new_word_ids == old_text.word_ids:
        return
    new_text = Text(
        id=old_text.id,
        display_name=old_text.display_name,
        word_ids=new_word_ids,
        category=old_text.category,
        unlock_threshold=old_text.unlock_threshold,
    )
    model.texts[old_text.id] = new_text
    model.text_list[idx] = new_text
