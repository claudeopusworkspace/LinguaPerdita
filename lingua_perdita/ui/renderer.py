"""Drawing primitives for the UI."""

from __future__ import annotations

import pygame

from lingua_perdita.ui.theme import (
    BG,
    BORDER,
    DARK_GRAY,
    FONT_SIZE,
    FONT_SIZE_SMALL,
    SCREEN_H,
    SCREEN_W,
    WHITE,
    get_font,
)


class Renderer:
    """Drawing utilities operating on a pygame surface."""

    def __init__(self, surface: pygame.Surface) -> None:
        self.surface = surface
        self._scanline_surface: pygame.Surface | None = None

    def clear(self) -> None:
        self.surface.fill(BG)

    def text(
        self,
        x: int,
        y: int,
        text: str,
        color: tuple = WHITE,
        size: int = FONT_SIZE,
        max_width: int = 0,
    ) -> int:
        """Render text with optional word wrap. Returns y after text."""
        font = get_font(size)

        if not max_width:
            rendered = font.render(text, True, color)
            self.surface.blit(rendered, (x, y))
            return y + rendered.get_height()

        # Word wrap
        words = text.split(" ")
        lines: list[str] = []
        current_line = ""

        for word in words:
            test = f"{current_line} {word}".strip()
            if font.size(test)[0] <= max_width:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        for line in lines:
            rendered = font.render(line, True, color)
            self.surface.blit(rendered, (x, y))
            y += rendered.get_height() + 2

        return y

    def box(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        color: tuple = BORDER,
        fill: tuple | None = None,
        title: str = "",
    ) -> None:
        """Draw a bordered box with optional fill and title."""
        rect = pygame.Rect(x, y, width, height)
        if fill:
            pygame.draw.rect(self.surface, fill, rect)
        pygame.draw.rect(self.surface, color, rect, 1)

        if title:
            font = get_font(FONT_SIZE_SMALL)
            rendered = font.render(title, True, color)
            self.surface.blit(rendered, (x + 6, y + 2))

    def hline(self, x: int, y: int, width: int, color: tuple = BORDER) -> None:
        pygame.draw.line(self.surface, color, (x, y), (x + width, y))

    def progress_bar(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        progress: float,
        color: tuple,
        bg_color: tuple = DARK_GRAY,
        label: str = "",
    ) -> None:
        """Draw a progress bar (0.0 to 1.0)."""
        progress = max(0.0, min(1.0, progress))
        rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.surface, bg_color, rect)

        if progress > 0:
            fill_rect = pygame.Rect(x, y, int(width * progress), height)
            pygame.draw.rect(self.surface, color, fill_rect)

        pygame.draw.rect(self.surface, BORDER, rect, 1)

        if label:
            font = get_font(FONT_SIZE_SMALL)
            rendered = font.render(label, True, WHITE)
            lx = x + (width - rendered.get_width()) // 2
            ly = y + (height - rendered.get_height()) // 2
            self.surface.blit(rendered, (lx, ly))

    def apply_scanlines(self) -> None:
        """CRT scanline overlay (cached)."""
        if self._scanline_surface is None:
            self._scanline_surface = pygame.Surface(
                (SCREEN_W, SCREEN_H), pygame.SRCALPHA
            )
            for sy in range(0, SCREEN_H, 3):
                pygame.draw.line(
                    self._scanline_surface,
                    (0, 0, 0, 20),
                    (0, sy), (SCREEN_W, sy),
                )
        self.surface.blit(self._scanline_surface, (0, 0))
