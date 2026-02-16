"""All balance tuning values for Lingua Perdita.

Every numeric knob lives here for fast iteration.
Never hardcode balance numbers elsewhere.
"""

# ── Click ────────────────────────────────────────────────────────────

CLICK_BASE_VALUE = 1.0

# ── Word costs by category ───────────────────────────────────────────

WORD_COST_RANGES = {
    "common": (10, 30),
    "everyday": (50, 200),
    "academic": (300, 1000),
    "rare": (1500, 5000),
}

# How many words per category (must sum to 30 for MVP)
WORDS_PER_CATEGORY = {
    "common": 10,
    "everyday": 10,
    "academic": 6,
    "rare": 4,
}

# ── Tools (repeatable generators) ────────────────────────────────────

TOOLS = [
    {
        "id": "worn_dictionary",
        "name": "Worn Dictionary",
        "base_cost": 15,
        "rate": 0.5,
        "scaling": 1.15,
    },
    {
        "id": "reference_grammar",
        "name": "Reference Grammar",
        "base_cost": 100,
        "rate": 3.0,
        "scaling": 1.18,
    },
    {
        "id": "comparative_lexicon",
        "name": "Comparative Lexicon",
        "base_cost": 800,
        "rate": 15.0,
        "scaling": 1.22,
    },
    {
        "id": "analytical_engine",
        "name": "Analytical Engine",
        "base_cost": 5000,
        "rate": 60.0,
        "scaling": 1.30,
    },
]

# ── One-time upgrades ────────────────────────────────────────────────

UPGRADES = [
    {
        "id": "upg_click_boost",
        "name": "Sharper Instinct",
        "description": "Clicking yields +2 more Insight",
        "cost": 50,
        "effect_type": "CLICK_FLAT",
        "effect_value": 2.0,
    },
    {
        "id": "upg_click_mult",
        "name": "Eureka Moments",
        "description": "Clicking yields 2x Insight",
        "cost": 500,
        "effect_type": "CLICK_MULT",
        "effect_value": 2.0,
    },
    {
        "id": "upg_production_boost",
        "name": "Research Methodology",
        "description": "+25% Insight production",
        "cost": 300,
        "effect_type": "PRODUCTION_ADD_PCT",
        "effect_value": 0.25,
    },
    {
        "id": "upg_text_efficiency",
        "name": "Contextual Analysis",
        "description": "+50% Insight from translated texts",
        "cost": 1500,
        "effect_type": "TEXT_EFFICIENCY",
        "effect_value": 1.5,
    },
    {
        "id": "upg_study_focus",
        "name": "Deep Study",
        "description": "Clicking yields 3x Insight",
        "cost": 3000,
        "effect_type": "CLICK_MULT",
        "effect_value": 3.0,
    },
]

# ── Roots ────────────────────────────────────────────────────────────

WORDS_PER_ROOT = 6
ROOT_COUNT = 5
ROOT_DISCOVERY_THRESHOLD = 3  # words translated to discover a root
ROOT_COST_MULTIPLIER = 0.7    # 30% discount on related words

# ── Texts ────────────────────────────────────────────────────────────

TEXT_COUNT = 4
TEXT_WORD_SLOTS_RANGE = (8, 12)  # words per text (with repetition)
INSIGHT_PER_TRANSLATED_WORD = 0.5  # Insight/s per translated word in a text
TEXT_EFFICIENCY_MULT = 1.0  # multiplied by upg_text_efficiency

# Text unlock thresholds (total words translated)
TEXT_UNLOCK_THRESHOLDS = [0, 5, 12, 20]

# ── Language generation ──────────────────────────────────────────────

ALPHABET_SIZE = 26
DEFAULT_SEED = 42
DEFAULT_PRESET = "runic"

# Glyph counts per word: common=1, others=2
GLYPHS_PER_WORD = {
    "common": 1,
    "everyday": 2,
    "academic": 2,
    "rare": 2,
}

# ── Pacing targets (for simulation validation) ──────────────────────

PACING_FIRST_WORD_MIN = 15.0       # seconds
PACING_FIRST_WORD_MAX = 120.0      # 2 minutes
PACING_FIRST_ROOT_MIN = 300.0      # 5 minutes
PACING_FIRST_ROOT_MAX = 1800.0     # 30 minutes
PACING_ALL_WORDS_MIN = 3600.0      # 1 hour
PACING_ALL_WORDS_MAX = 7200.0      # 2 hours
PACING_MAX_EARLY_GAP = 300.0       # 5 minutes (first 30 min)
PACING_MAX_LATE_GAP = 600.0        # 10 minutes (after 30 min)
PACING_MAX_DEAD_TIME_RATIO = 0.30  # 30%

# ── Simulation ───────────────────────────────────────────────────────

SIM_CLICK_RATE = 3.0       # clicks per second
SIM_TIME_CAP = 14400.0     # 4 hours max
SIM_TICK_RESOLUTION = 1.0  # seconds per simulation tick
