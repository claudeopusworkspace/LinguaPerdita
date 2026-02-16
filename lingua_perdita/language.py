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
    ],
    "everyday": [
        "gather", "build", "speak", "listen", "travel", "carry", "break",
        "mend", "trade", "plant", "harvest", "shelter", "guard", "rest",
        "weave",
    ],
    "academic": [
        "knowledge", "theorem", "axiom", "paradox", "chronicle", "alchemy",
        "cipher", "cosmology", "dialectic", "epitome",
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


def generate_language(seed: int = DEFAULT_SEED) -> LanguageModel:
    """Generate a complete LanguageModel from a seed. Deterministic."""
    rng = random.Random(seed)
    model = LanguageModel(seed=seed)

    # ── Generate words ───────────────────────────────────────────────
    all_words: list[Word] = []
    word_index = 0

    for category, count in WORDS_PER_CATEGORY.items():
        meanings = list(_MEANINGS[category])
        rng.shuffle(meanings)
        cost_lo, cost_hi = WORD_COST_RANGES[category]
        glyph_count = GLYPHS_PER_WORD[category]

        for i in range(count):
            meaning = meanings[i % len(meanings)]
            # Spread costs across the range
            if count > 1:
                t = i / (count - 1)
            else:
                t = 0.5
            base_cost = int(cost_lo + t * (cost_hi - cost_lo))

            # Deterministic glyph assignment
            glyph_indices = tuple(
                (word_index * 7 + g * 13) % ALPHABET_SIZE
                for g in range(glyph_count)
            )

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
        category_words = [w for w in all_words if w.category == category]
        other_words = [w for w in all_words if w.category != category]

        text_word_ids: list[str] = []
        for si in range(slot_count):
            if category_words and (rng.random() < 0.6 or not other_words):
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

    return model
