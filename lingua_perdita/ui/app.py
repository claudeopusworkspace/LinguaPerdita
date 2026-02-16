"""Main application loop and screen management."""

from __future__ import annotations

import pygame

from lingua_perdita.constants import DEFAULT_PRESET, DEFAULT_SEED
from lingua_perdita.glyphs import GlyphRenderer
from lingua_perdita.language import generate_language
from lingua_perdita.presenter import GamePresenter
from lingua_perdita.save import get_save_seed, has_save, load_game, save_game
from lingua_perdita.ui.renderer import Renderer
from lingua_perdita.ui.screens import LexiconScreen, Screen, ShopScreen, TabletScreen
from lingua_perdita.ui.theme import (
    BG,
    BG_DARK,
    BORDER,
    CONTENT_LEFT,
    CONTENT_WIDTH,
    DARK_GRAY,
    FPS,
    FONT_SIZE,
    FONT_SIZE_LARGE,
    FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
    GOLD,
    GOLD_BRIGHT,
    GOLD_DIM,
    GRAY,
    HEADER_HEIGHT,
    HOVER_BG,
    NOTIF_BG,
    NOTIF_COLORS,
    NOTIF_DURATION,
    NOTIF_INFO,
    NOTIF_MILESTONE,
    NOTIF_ROOT,
    PADDING,
    SCREEN_H,
    SCREEN_W,
    STATUS_BAR_HEIGHT,
    TAB_HEIGHT,
    TEXT_DIM,
    TICK_INTERVAL,
    WHITE,
    format_number,
    format_rate,
    get_font,
)


class App:
    """Main application managing screens, input, and game loop."""

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Lingua Perdita")
        self.clock = pygame.time.Clock()
        self.renderer = Renderer(self.screen)
        self.running = True

        # Determine seed (load from save or use default)
        seed = DEFAULT_SEED
        saved_seed = get_save_seed()
        if saved_seed is not None:
            seed = saved_seed

        # Create game
        language = generate_language(seed)
        self.presenter = GamePresenter(language=language, seed=seed)
        self.glyph_renderer = GlyphRenderer(seed=seed, preset=DEFAULT_PRESET)

        # Load save if exists
        if has_save():
            loaded_seed = load_game(self.presenter.runtime)
            if loaded_seed is not None:
                self.presenter.restore_milestones_seen()

        # Screens
        self._screens: list[Screen] = [
            TabletScreen(),
            ShopScreen(),
            LexiconScreen(),
        ]
        self.active_screen: int = 0

        # Tab rects (rebuilt each frame)
        self._tab_rects: list[tuple[pygame.Rect, int]] = []

        # Notifications
        self._notifications: list[tuple[str, float, str]] = []  # (msg, remaining, type)

        # Tick accumulator
        self._tick_acc: float = 0.0

        # Auto-save timer
        self._autosave_timer: float = 60.0

    def run(self) -> None:
        """Main loop."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()
            pygame.display.flip()

        # Save on exit
        save_game(self.presenter.runtime, self.presenter.language.seed)
        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return

                # Screen switching
                if event.key == pygame.K_TAB:
                    self.active_screen = (self.active_screen + 1) % len(self._screens)
                    continue
                if event.key == pygame.K_1:
                    self.active_screen = 0
                    continue
                if event.key == pygame.K_2:
                    self.active_screen = 1
                    continue
                if event.key == pygame.K_3:
                    self.active_screen = 2
                    continue

                # Ctrl+S save
                if event.key == pygame.K_s and (event.mod & pygame.KMOD_CTRL):
                    save_game(self.presenter.runtime, self.presenter.language.seed)
                    self._notifications.append(("Game saved!", NOTIF_DURATION, NOTIF_INFO))
                    continue

            # Check main tab bar click
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for rect, idx in self._tab_rects:
                    if rect.collidepoint(event.pos):
                        self.active_screen = idx
                        break
                else:
                    # Pass to active screen
                    result = self._screens[self.active_screen].handle_event(event, self.presenter)
                    if result:
                        self._switch_to_screen(result)
                continue

            # Pass other events to active screen
            self._screens[self.active_screen].handle_event(event, self.presenter)

    def _update(self, dt: float) -> None:
        # Fixed game ticks
        self._tick_acc += dt
        while self._tick_acc >= TICK_INTERVAL:
            self.presenter.tick(TICK_INTERVAL)
            self._tick_acc -= TICK_INTERVAL

        # Update active screen
        self._screens[self.active_screen].update(dt)

        # Check for new milestones
        new_milestones = self.presenter.pop_new_milestones()
        for mid in new_milestones:
            text = self.presenter.get_milestone_text(mid)
            ntype = NOTIF_ROOT if mid.startswith("root_") else NOTIF_MILESTONE
            self._notifications.append((text, NOTIF_DURATION, ntype))

        # Decay notifications
        self._notifications = [
            (msg, remaining - dt, ntype)
            for msg, remaining, ntype in self._notifications
            if remaining - dt > 0
        ]

        # Auto-save
        self._autosave_timer -= dt
        if self._autosave_timer <= 0:
            save_game(self.presenter.runtime, self.presenter.language.seed)
            self._autosave_timer = 60.0

    def _draw(self) -> None:
        self.renderer.clear()
        self._draw_header()
        self._draw_tabs()
        self._screens[self.active_screen].draw(
            self.renderer, self.presenter, self.glyph_renderer
        )
        self._draw_status_bar()
        self._draw_notifications()
        self._update_cursor()
        self.renderer.apply_scanlines()

    def _draw_header(self) -> None:
        # Background
        pygame.draw.rect(self.screen, BG_DARK, (0, 0, SCREEN_W, HEADER_HEIGHT))

        font_large = get_font(FONT_SIZE_LARGE)
        font = get_font(FONT_SIZE)
        font_sm = get_font(FONT_SIZE_SMALL)

        # Title
        title = font_large.render("LINGUA PERDITA", True, GOLD)
        self.screen.blit(title, (PADDING, 8))

        # Subtitle
        subtitle = font_sm.render("Excavation I — The Foundation Tablet", True, TEXT_DIM)
        self.screen.blit(subtitle, (PADDING, 36))

        # Insight display (right side)
        insight = self.presenter.insight_value()
        rate = self.presenter.insight_rate()

        value_text = font_large.render(f"{format_number(insight)} Insight", True, GOLD_BRIGHT)
        self.screen.blit(value_text, (SCREEN_W - value_text.get_width() - PADDING, 8))

        rate_text = font_sm.render(format_rate(rate), True, GOLD_DIM)
        self.screen.blit(rate_text, (SCREEN_W - rate_text.get_width() - PADDING, 36))

        # Separator
        self.renderer.hline(0, HEADER_HEIGHT - 1, SCREEN_W, BORDER)

    def _draw_tabs(self) -> None:
        self._tab_rects.clear()
        mouse_pos = pygame.mouse.get_pos()
        tab_w = SCREEN_W // len(self._screens)
        y = HEADER_HEIGHT

        for i, screen in enumerate(self._screens):
            is_active = i == self.active_screen
            tab_rect = pygame.Rect(i * tab_w, y, tab_w - 1, TAB_HEIGHT)
            self._tab_rects.append((tab_rect, i))

            is_hovered = tab_rect.collidepoint(mouse_pos) and not is_active

            if is_active:
                color, bg = GOLD_BRIGHT, DARK_GRAY
            elif is_hovered:
                color, bg = GOLD, HOVER_BG
            else:
                color, bg = GOLD_DIM, BG_DARK

            pygame.draw.rect(self.screen, bg, tab_rect)
            pygame.draw.rect(self.screen, color if is_active else BORDER, tab_rect, 1)

            font = get_font(FONT_SIZE_SMALL)
            label = f"{i + 1}:{screen.name}"
            rendered = font.render(label, True, color)
            tx = tab_rect.x + (tab_rect.width - rendered.get_width()) // 2
            ty = tab_rect.y + (tab_rect.height - rendered.get_height()) // 2
            self.screen.blit(rendered, (tx, ty))

    def _draw_status_bar(self) -> None:
        y = SCREEN_H - STATUS_BAR_HEIGHT
        pygame.draw.rect(self.screen, BG_DARK, (0, y, SCREEN_W, STATUS_BAR_HEIGHT))
        self.renderer.hline(0, y, SCREEN_W, BORDER)

        font = get_font(FONT_SIZE_TINY)
        help_text = "TAB/1-3: Switch  |  CLICK: Insight/Buy  |  SCROLL: Navigate  |  CTRL+S: Save  |  ESC: Quit"
        rendered = font.render(help_text, True, TEXT_DIM)
        self.screen.blit(rendered, (PADDING, y + 8))

        # Words progress on right
        total = len(self.presenter.language.word_list)
        translated = self.presenter.total_words_translated()
        progress = font.render(f"Words: {translated}/{total}", True, GRAY)
        self.screen.blit(progress, (SCREEN_W - progress.get_width() - PADDING, y + 8))

    def _draw_notifications(self) -> None:
        y = HEADER_HEIGHT + TAB_HEIGHT + PADDING
        font = get_font(FONT_SIZE_SMALL)

        for msg, remaining, ntype in self._notifications[:3]:
            alpha = min(1.0, remaining / 1.0)  # Fade in last second
            color = NOTIF_COLORS.get(ntype, GOLD)
            bg = NOTIF_BG.get(ntype, (25, 20, 10))

            # Fade color
            faded = tuple(int(c * alpha) for c in color)
            faded_bg = tuple(int(c * alpha) for c in bg)

            rect_w = min(350, SCREEN_W // 3)
            rect = pygame.Rect(SCREEN_W - rect_w - PADDING, y, rect_w, 28)

            pygame.draw.rect(self.screen, faded_bg, rect)
            pygame.draw.rect(self.screen, faded, rect, 1)

            rendered = font.render(msg[:40], True, faded)
            self.screen.blit(rendered, (rect.x + 6, rect.y + 5))

            y += 34

    def _update_cursor(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        is_interactive = False

        # Tab bar
        for rect, _ in self._tab_rects:
            if rect.collidepoint(mouse_pos):
                is_interactive = True
                break

        # Active screen interactive rects
        if not is_interactive:
            for rect in self._screens[self.active_screen].get_interactive_rects():
                if rect.collidepoint(mouse_pos):
                    is_interactive = True
                    break

        try:
            pygame.mouse.set_cursor(
                pygame.SYSTEM_CURSOR_HAND if is_interactive else pygame.SYSTEM_CURSOR_ARROW
            )
        except pygame.error:
            pass  # Headless/dummy video driver

    def _switch_to_screen(self, name: str) -> None:
        for i, screen in enumerate(self._screens):
            if screen.name == name:
                self.active_screen = i
                return


def run_app() -> None:
    """Launch the game."""
    app = App()
    app.run()
