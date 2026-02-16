"""GlyphForge integration — render procedural glyphs to pygame surfaces.

Generates an alphabet from a seed+preset, then renders individual glyphs
and word sequences as cached pygame Surfaces.
"""

from __future__ import annotations

import sys
from typing import Sequence

import pygame

sys.path.insert(0, "/workspace/glyphforge")
import glyphforge
from glyphforge.alphabet import Alphabet
from glyphforge.glyph import Glyph

from lingua_perdita.constants import DEFAULT_PRESET, DEFAULT_SEED
from lingua_perdita.language import Word


class GlyphRenderer:
    """Render GlyphForge glyphs as pygame surfaces with caching."""

    def __init__(self, seed: int = DEFAULT_SEED, preset: str = DEFAULT_PRESET):
        self.alphabet: Alphabet = glyphforge.generate(seed=seed, preset=preset)
        self._cache: dict[tuple, pygame.Surface] = {}

    def render_glyph(
        self,
        index: int,
        size: int = 32,
        color: tuple[int, int, int] = (200, 200, 180),
    ) -> pygame.Surface:
        """Render a single glyph to a pygame Surface (cached).

        Args:
            index: Glyph index (0-25).
            size: Pixel height of the output surface.
            color: RGB fill color.
        """
        key = ("glyph", index, size, color)
        if key in self._cache:
            return self._cache[key]

        glyph = self.alphabet[index]
        surface = self._rasterize_glyph(glyph, size, color)
        self._cache[key] = surface
        return surface

    def render_word(
        self,
        word: Word,
        size: int = 32,
        color: tuple[int, int, int] = (200, 200, 180),
        spacing: int = 4,
    ) -> pygame.Surface:
        """Render a word as a horizontal sequence of glyphs (cached).

        Args:
            word: Word object with glyph_indices.
            size: Pixel height per glyph.
            color: RGB fill color.
            spacing: Pixels between glyphs.
        """
        key = ("word", word.id, size, color)
        if key in self._cache:
            return self._cache[key]

        glyph_surfaces = [
            self.render_glyph(idx, size, color)
            for idx in word.glyph_indices
        ]

        if not glyph_surfaces:
            surface = pygame.Surface((size, size), pygame.SRCALPHA)
            self._cache[key] = surface
            return surface

        total_width = sum(s.get_width() for s in glyph_surfaces) + spacing * (len(glyph_surfaces) - 1)
        max_height = max(s.get_height() for s in glyph_surfaces)

        surface = pygame.Surface((total_width, max_height), pygame.SRCALPHA)
        x = 0
        for gs in glyph_surfaces:
            y_offset = (max_height - gs.get_height()) // 2
            surface.blit(gs, (x, y_offset))
            x += gs.get_width() + spacing

        self._cache[key] = surface
        return surface

    def clear_cache(self) -> None:
        """Clear the surface cache (e.g., on theme change)."""
        self._cache.clear()

    def _rasterize_glyph(
        self,
        glyph: Glyph,
        size: int,
        color: tuple[int, int, int],
    ) -> pygame.Surface:
        """Rasterize a single Glyph's outline polygons to a pygame Surface."""
        outline = glyph.outline
        bounds = outline.bounds

        if bounds.area < 1e-12:
            return pygame.Surface((size, size), pygame.SRCALPHA)

        # Compute scale to fit within size x size, preserving aspect ratio
        aspect = bounds.width / max(bounds.height, 1e-12)
        if aspect > 1.0:
            w = size
            h = max(1, int(size / aspect))
        else:
            h = size
            w = max(1, int(size * aspect))

        surface = pygame.Surface((w, h), pygame.SRCALPHA)

        sx = (w - 2) / max(bounds.width, 1e-12)
        sy = (h - 2) / max(bounds.height, 1e-12)
        scale = min(sx, sy)

        # Center the glyph
        glyph_w = bounds.width * scale
        glyph_h = bounds.height * scale
        offset_x = (w - glyph_w) / 2
        offset_y = (h - glyph_h) / 2

        for polygon in outline.polygons:
            if len(polygon) < 3:
                continue

            # Transform points: normalize to bounds, scale, flip Y for screen coords
            points = []
            for pt in polygon:
                px = (pt.x - bounds.x_min) * scale + offset_x
                # Flip Y: GlyphForge Y increases upward, pygame Y increases downward
                py = h - ((pt.y - bounds.y_min) * scale + offset_y)
                points.append((px, py))

            pygame.draw.polygon(surface, color, points)

        return surface
