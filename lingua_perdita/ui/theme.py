"""Visual theme constants — dark stone/parchment aesthetic."""

import pygame

# ── Colors ────────────────────────────────────────────────────────────

BG = (15, 12, 10)
BG_PANEL = (22, 18, 15)
BG_DARK = (10, 8, 6)

# Currency / primary
GOLD = (220, 180, 50)
GOLD_DIM = (130, 100, 30)
GOLD_BRIGHT = (255, 220, 80)

# Glyphs / stone
STONE = (140, 130, 110)
STONE_DIM = (80, 75, 65)

# Translated words
GREEN = (60, 200, 80)
GREEN_DIM = (30, 100, 40)

# Root discoveries
CYAN = (60, 200, 220)
CYAN_DIM = (30, 100, 110)

# UI elements
WHITE = (200, 200, 180)
GRAY = (100, 95, 85)
DARK_GRAY = (40, 36, 30)
TEXT_DIM = (70, 65, 55)
HOVER_BG = (35, 30, 25)
BORDER = (60, 55, 45)
RED = (200, 60, 40)
RED_DIM = (120, 30, 20)

# ── Layout ────────────────────────────────────────────────────────────

SCREEN_W = 1024
SCREEN_H = 768
FPS = 30
TICK_INTERVAL = 0.1  # 100ms game ticks

FONT_SIZE = 18
FONT_SIZE_LARGE = 24
FONT_SIZE_SMALL = 14
FONT_SIZE_TINY = 11

PADDING = 12
LINE_HEIGHT = 22
LINE_HEIGHT_SMALL = 18

HEADER_HEIGHT = 60
TAB_HEIGHT = 32
STATUS_BAR_HEIGHT = 28

CONTENT_TOP = HEADER_HEIGHT + TAB_HEIGHT + PADDING
CONTENT_BOTTOM = SCREEN_H - STATUS_BAR_HEIGHT - PADDING
CONTENT_LEFT = PADDING
CONTENT_RIGHT = SCREEN_W - PADDING
CONTENT_WIDTH = CONTENT_RIGHT - CONTENT_LEFT
CONTENT_HEIGHT = CONTENT_BOTTOM - CONTENT_TOP

# ── Notification ──────────────────────────────────────────────────────

NOTIF_ROOT = "root"
NOTIF_MILESTONE = "milestone"
NOTIF_INFO = "info"

NOTIF_COLORS = {
    NOTIF_ROOT: CYAN,
    NOTIF_MILESTONE: GREEN,
    NOTIF_INFO: GOLD,
}

NOTIF_BG = {
    NOTIF_ROOT: (10, 25, 30),
    NOTIF_MILESTONE: (10, 30, 15),
    NOTIF_INFO: (30, 25, 10),
}

NOTIF_DURATION = 4.0  # seconds

# ── Font ──────────────────────────────────────────────────────────────

_font_cache: dict[int, pygame.font.Font] = {}


def get_font(size: int = FONT_SIZE) -> pygame.font.Font:
    """Get a cached font at the given size."""
    if size not in _font_cache:
        _font_cache[size] = pygame.font.Font(None, size)
    return _font_cache[size]


# ── Helpers ───────────────────────────────────────────────────────────

def format_number(value: float) -> str:
    """Format a number for display."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 10_000:
        return f"{value / 1_000:.1f}K"
    if value >= 100:
        return f"{value:,.0f}"
    if value >= 1:
        return f"{value:.1f}"
    if value >= 0.01:
        return f"{value:.2f}"
    return f"{value:.3f}"


def format_rate(rate: float) -> str:
    """Format a rate for display with +/- sign."""
    sign = "+" if rate >= 0 else ""
    return f"{sign}{format_number(rate)}/s"
