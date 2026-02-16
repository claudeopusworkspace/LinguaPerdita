"""Game screens: Tablet, Shop, Lexicon."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from lingua_perdita.ui.theme import (
    BG_DARK,
    BG_PANEL,
    BORDER,
    CONTENT_BOTTOM,
    CONTENT_HEIGHT,
    CONTENT_LEFT,
    CONTENT_RIGHT,
    CONTENT_TOP,
    CONTENT_WIDTH,
    CYAN,
    CYAN_DIM,
    DARK_GRAY,
    FONT_SIZE,
    FONT_SIZE_LARGE,
    FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
    GOLD,
    GOLD_BRIGHT,
    GOLD_DIM,
    GRAY,
    GREEN,
    GREEN_DIM,
    HOVER_BG,
    LINE_HEIGHT,
    LINE_HEIGHT_SMALL,
    PADDING,
    RED,
    STONE,
    STONE_DIM,
    TEXT_DIM,
    WHITE,
    format_number,
    format_rate,
    get_font,
)

if TYPE_CHECKING:
    from lingua_perdita.glyphs import GlyphRenderer
    from lingua_perdita.presenter import GamePresenter
    from lingua_perdita.ui.renderer import Renderer


class Screen:
    """Base screen class."""
    name: str = ""

    def draw(self, r: Renderer, presenter: GamePresenter, glyph_renderer: GlyphRenderer) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def handle_event(self, event: pygame.event.Event, presenter: GamePresenter) -> str | None:
        return None

    def get_interactive_rects(self) -> list[pygame.Rect]:
        return []


# ═════════════════════════════════════════════════════════════════════
# TABLET SCREEN — Core gameplay
# ═════════════════════════════════════════════════════════════════════

class TabletScreen(Screen):
    """Shows selected text as a grid of word slots. Click for Insight."""

    name = "TABLET"

    def __init__(self) -> None:
        self.selected_text_idx: int = 0
        self._word_rects: list[tuple[pygame.Rect, str]] = []
        self._text_tab_rects: list[tuple[pygame.Rect, int]] = []
        self._click_flash: float = 0.0

    def update(self, dt: float) -> None:
        if self._click_flash > 0:
            self._click_flash -= dt

    def draw(self, r: Renderer, presenter: GamePresenter, glyph_renderer: GlyphRenderer) -> None:
        self._word_rects.clear()
        self._text_tab_rects.clear()
        mouse_pos = pygame.mouse.get_pos()

        # ── Text selector tabs ───────────────────────────────────────
        tab_y = CONTENT_TOP
        tab_w = CONTENT_WIDTH // max(len(presenter.language.text_list), 1)

        for ti, text in enumerate(presenter.language.text_list):
            is_unlocked = presenter.is_text_unlocked(text.id)
            is_available = presenter.is_text_available(text.id)
            is_active = ti == self.selected_text_idx

            tab_rect = pygame.Rect(CONTENT_LEFT + ti * tab_w, tab_y, tab_w - 2, 28)
            self._text_tab_rects.append((tab_rect, ti))

            if not is_unlocked and not is_available:
                color = TEXT_DIM
                bg = BG_DARK
                label = "???"
            elif is_active:
                color = GOLD_BRIGHT
                bg = DARK_GRAY
                label = text.display_name[:20]
            elif tab_rect.collidepoint(mouse_pos):
                color = GOLD
                bg = HOVER_BG
                label = text.display_name[:20]
            else:
                color = GOLD_DIM if is_unlocked else TEXT_DIM
                bg = BG_PANEL
                label = text.display_name[:20] if is_unlocked else "Locked"

            pygame.draw.rect(r.surface, bg, tab_rect)
            pygame.draw.rect(r.surface, color, tab_rect, 1)
            font = get_font(FONT_SIZE_TINY)
            rendered = font.render(label, True, color)
            r.surface.blit(rendered, (tab_rect.x + 4, tab_rect.y + 6))

        # ── Text content area ────────────────────────────────────────
        content_y = tab_y + 36

        # Get selected text
        if self.selected_text_idx >= len(presenter.language.text_list):
            self.selected_text_idx = 0

        text = presenter.language.text_list[self.selected_text_idx]

        if not presenter.is_text_unlocked(text.id):
            # Show unlock requirement
            font = get_font(FONT_SIZE)
            threshold = text.unlock_threshold
            current = presenter.total_words_translated()
            msg = f"Translate {threshold} words to unlock ({current}/{threshold})"
            rendered = font.render(msg, True, TEXT_DIM)
            cx = CONTENT_LEFT + (CONTENT_WIDTH - rendered.get_width()) // 2
            r.surface.blit(rendered, (cx, content_y + 50))
            return

        # Show text info bar
        translated = presenter.text_translated_count(text.id)
        total = presenter.text_total_unique_words(text.id)
        font_sm = get_font(FONT_SIZE_SMALL)
        info = f"{text.display_name}  —  {translated}/{total} words translated"
        rendered = font_sm.render(info, True, GRAY)
        r.surface.blit(rendered, (CONTENT_LEFT, content_y))
        content_y += LINE_HEIGHT_SMALL + 4

        # ── Word grid ────────────────────────────────────────────────
        grid_x = CONTENT_LEFT + PADDING
        grid_y = content_y + 4
        cell_w = 120
        cell_h = 60
        cell_pad = 8
        cols = max(1, (CONTENT_WIDTH - 2 * PADDING) // (cell_w + cell_pad))

        for slot_idx, word_id in enumerate(text.word_ids):
            word = presenter.language.words[word_id]
            col = slot_idx % cols
            row = slot_idx // cols

            x = grid_x + col * (cell_w + cell_pad)
            y = grid_y + row * (cell_h + cell_pad)

            if y + cell_h > CONTENT_BOTTOM:
                break

            cell_rect = pygame.Rect(x, y, cell_w, cell_h)
            is_hovered = cell_rect.collidepoint(mouse_pos)
            is_translated = presenter.is_word_translated(word_id)

            # Background
            if is_translated:
                bg = (20, 35, 20)
            elif is_hovered:
                bg = HOVER_BG
            else:
                bg = BG_PANEL

            pygame.draw.rect(r.surface, bg, cell_rect)
            pygame.draw.rect(r.surface, GREEN_DIM if is_translated else BORDER, cell_rect, 1)

            if is_translated:
                # Show English meaning
                font = get_font(FONT_SIZE_SMALL)
                rendered = font.render(word.meaning, True, GREEN)
                tx = x + (cell_w - rendered.get_width()) // 2
                ty = y + (cell_h - rendered.get_height()) // 2
                r.surface.blit(rendered, (tx, ty))
            else:
                # Show glyph(s)
                glyph_color = STONE if not is_hovered else WHITE
                glyph_surface = glyph_renderer.render_word(word, 32, glyph_color)
                gx = x + (cell_w - glyph_surface.get_width()) // 2
                gy = y + (cell_h - glyph_surface.get_height()) // 2
                r.surface.blit(glyph_surface, (gx, gy))

                self._word_rects.append((cell_rect, word_id))

        # ── Click flash effect ───────────────────────────────────────
        if self._click_flash > 0:
            alpha = int(self._click_flash / 0.15 * 30)
            flash_surf = pygame.Surface((CONTENT_WIDTH, CONTENT_HEIGHT), pygame.SRCALPHA)
            flash_surf.fill((255, 220, 80, alpha))
            r.surface.blit(flash_surf, (CONTENT_LEFT, CONTENT_TOP))

    def handle_event(self, event: pygame.event.Event, presenter: GamePresenter) -> str | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check text tabs
            for rect, idx in self._text_tab_rects:
                if rect.collidepoint(event.pos):
                    text = presenter.language.text_list[idx]
                    if presenter.is_text_unlocked(text.id) or presenter.is_text_available(text.id):
                        self.selected_text_idx = idx
                    return None

            # Click on untranslated word slots for insight
            for rect, word_id in self._word_rects:
                if rect.collidepoint(event.pos):
                    presenter.process_click()
                    self._click_flash = 0.15
                    return None

            # Click anywhere in content area for insight
            content_rect = pygame.Rect(CONTENT_LEFT, CONTENT_TOP, CONTENT_WIDTH, CONTENT_HEIGHT)
            if content_rect.collidepoint(event.pos):
                presenter.process_click()
                self._click_flash = 0.15

        return None

    def get_interactive_rects(self) -> list[pygame.Rect]:
        rects = [r for r, _ in self._text_tab_rects]
        rects.extend(r for r, _ in self._word_rects)
        return rects


# ═════════════════════════════════════════════════════════════════════
# SHOP SCREEN — Purchase tools, words, upgrades
# ═════════════════════════════════════════════════════════════════════

class ShopScreen(Screen):
    """Purchase tools, translate words, buy upgrades."""

    name = "SHOP"

    TABS = ["Tools", "Words", "Upgrades"]

    def __init__(self) -> None:
        self.selected_tab: int = 0
        self._item_rects: list[tuple[pygame.Rect, str]] = []
        self._subtab_rects: list[tuple[pygame.Rect, int]] = []
        self._purchase_flash: dict[str, float] = {}
        self.scroll_offset: int = 0

    def update(self, dt: float) -> None:
        expired = [k for k, v in self._purchase_flash.items() if v <= 0]
        for k in expired:
            del self._purchase_flash[k]
        for k in self._purchase_flash:
            self._purchase_flash[k] -= dt

    def draw(self, r: Renderer, presenter: GamePresenter, glyph_renderer: GlyphRenderer) -> None:
        self._item_rects.clear()
        self._subtab_rects.clear()
        mouse_pos = pygame.mouse.get_pos()

        # ── Sub-tabs ─────────────────────────────────────────────────
        tab_y = CONTENT_TOP
        tab_w = CONTENT_WIDTH // len(self.TABS)

        for i, tab_name in enumerate(self.TABS):
            is_active = i == self.selected_tab
            tab_rect = pygame.Rect(CONTENT_LEFT + i * tab_w, tab_y, tab_w - 2, 28)
            self._subtab_rects.append((tab_rect, i))

            if is_active:
                color, bg = GOLD_BRIGHT, DARK_GRAY
            elif tab_rect.collidepoint(mouse_pos):
                color, bg = GOLD, HOVER_BG
            else:
                color, bg = GOLD_DIM, BG_PANEL

            pygame.draw.rect(r.surface, bg, tab_rect)
            pygame.draw.rect(r.surface, color, tab_rect, 1)
            font = get_font(FONT_SIZE_SMALL)
            rendered = font.render(tab_name, True, color)
            r.surface.blit(rendered, (tab_rect.x + 8, tab_rect.y + 6))

        # ── Content based on tab ─────────────────────────────────────
        list_y = tab_y + 36 - self.scroll_offset

        if self.selected_tab == 0:
            list_y = self._draw_tools(r, presenter, list_y, mouse_pos)
        elif self.selected_tab == 1:
            list_y = self._draw_words(r, presenter, glyph_renderer, list_y, mouse_pos)
        elif self.selected_tab == 2:
            list_y = self._draw_upgrades(r, presenter, list_y, mouse_pos)

    def _draw_tools(self, r: Renderer, presenter: GamePresenter, y: int, mouse_pos: tuple) -> int:
        tools = presenter.get_tools()
        for edef, status in tools:
            y = self._draw_element_row(r, presenter, edef, status, y, mouse_pos, show_count=True)
        return y

    def _draw_words(self, r: Renderer, presenter: GamePresenter,
                    glyph_renderer: GlyphRenderer, y: int, mouse_pos: tuple) -> int:
        words = presenter.get_purchasable_words()

        if not words:
            font = get_font(FONT_SIZE)
            rendered = font.render("All words translated!", True, GREEN)
            r.surface.blit(rendered, (CONTENT_LEFT + PADDING, y))
            return y + LINE_HEIGHT

        for word, status in words:
            if y > CONTENT_BOTTOM:
                break
            if y + 56 < CONTENT_TOP + 36:
                y += 60
                continue

            row_rect = pygame.Rect(CONTENT_LEFT + 4, y, CONTENT_WIDTH - 8, 54)
            is_hovered = row_rect.collidepoint(mouse_pos)
            is_affordable = status is not None and status.affordable
            is_flashing = self._purchase_flash.get(word.id, 0) > 0

            # Background
            if is_flashing:
                alpha = self._purchase_flash[word.id] / 0.3
                bg = (int(20 + 40 * alpha), int(35 + 45 * alpha), int(20 + 30 * alpha))
            elif is_hovered and is_affordable:
                bg = HOVER_BG
            else:
                bg = BG_PANEL

            pygame.draw.rect(r.surface, bg, row_rect)
            pygame.draw.rect(r.surface, GREEN_DIM if is_affordable else BORDER, row_rect, 1)

            # Glyph
            glyph_color = STONE if is_affordable else STONE_DIM
            glyph_surf = glyph_renderer.render_word(word, 28, glyph_color)
            r.surface.blit(glyph_surf, (row_rect.x + 8, row_rect.y + (54 - glyph_surf.get_height()) // 2))

            # Cost
            cost = presenter.get_word_cost(word.id)
            cost_color = GOLD if is_affordable else TEXT_DIM
            font = get_font(FONT_SIZE_SMALL)
            cost_text = font.render(f"{format_number(cost)} Insight", True, cost_color)
            r.surface.blit(cost_text, (row_rect.right - cost_text.get_width() - 8,
                                       row_rect.y + 8))

            # Category and root
            root = presenter.language.roots[word.root_id]
            root_discovered = presenter.is_root_discovered(word.root_id)
            info_font = get_font(FONT_SIZE_TINY)

            cat_text = info_font.render(word.category, True, GRAY)
            r.surface.blit(cat_text, (row_rect.x + 60, row_rect.y + 8))

            if root_discovered:
                root_text = info_font.render(f"Root: {root.display_name} (30% off)", True, CYAN_DIM)
                r.surface.blit(root_text, (row_rect.x + 60, row_rect.y + 24))

            # Show text membership
            membership = presenter.word_text_membership(word.id)
            if membership:
                parts = []
                for _tid, name, unlocked in membership:
                    parts.append(name if unlocked else "???")
                in_text = info_font.render(f"In: {', '.join(parts)}", True, TEXT_DIM)
                r.surface.blit(in_text, (row_rect.x + 60, row_rect.y + 38))

            self._item_rects.append((row_rect, word.id))
            y += 60

        return y

    def _draw_upgrades(self, r: Renderer, presenter: GamePresenter, y: int, mouse_pos: tuple) -> int:
        upgrades = presenter.get_upgrades()
        for edef, status in upgrades:
            count = presenter.state.element_count(edef.id)
            if count >= (edef.max_count or 1):
                # Show as purchased
                row_rect = pygame.Rect(CONTENT_LEFT + 4, y, CONTENT_WIDTH - 8, 48)
                pygame.draw.rect(r.surface, (20, 30, 20), row_rect)
                pygame.draw.rect(r.surface, GREEN_DIM, row_rect, 1)
                font = get_font(FONT_SIZE_SMALL)
                rendered = font.render(f"{edef.display_name} — OWNED", True, GREEN_DIM)
                r.surface.blit(rendered, (row_rect.x + 8, row_rect.y + 8))
                desc = presenter.get_effect_summary(edef.id)
                if desc:
                    desc_text = get_font(FONT_SIZE_TINY).render(desc, True, TEXT_DIM)
                    r.surface.blit(desc_text, (row_rect.x + 8, row_rect.y + 28))
                y += 54
            else:
                y = self._draw_element_row(r, presenter, edef, status, y, mouse_pos)
        return y

    def _draw_element_row(
        self, r: Renderer, presenter: GamePresenter,
        edef, status, y: int, mouse_pos: tuple,
        show_count: bool = False,
    ) -> int:
        if y > CONTENT_BOTTOM or y + 60 < CONTENT_TOP + 36:
            return y + 66

        row_rect = pygame.Rect(CONTENT_LEFT + 4, y, CONTENT_WIDTH - 8, 60)
        is_hovered = row_rect.collidepoint(mouse_pos)
        is_affordable = status is not None and status.affordable
        is_flashing = self._purchase_flash.get(edef.id, 0) > 0

        if is_flashing:
            alpha = self._purchase_flash[edef.id] / 0.3
            bg = (int(20 + 40 * alpha), int(30 + 50 * alpha), int(15 + 35 * alpha))
        elif is_hovered and is_affordable:
            bg = HOVER_BG
        else:
            bg = BG_PANEL

        pygame.draw.rect(r.surface, bg, row_rect)
        pygame.draw.rect(r.surface, GOLD_DIM if is_affordable else BORDER, row_rect, 1)

        # Name
        font = get_font(FONT_SIZE_SMALL)
        name = edef.display_name
        if show_count:
            count = presenter.state.element_count(edef.id)
            name = f"{name} (x{count})"
        name_color = WHITE if is_affordable else GRAY
        rendered = font.render(name, True, name_color)
        r.surface.blit(rendered, (row_rect.x + 8, row_rect.y + 6))

        # Description / effect
        desc = presenter.get_effect_summary(edef.id)
        if not desc and isinstance(edef.description, str):
            desc = edef.description
        if desc:
            desc_font = get_font(FONT_SIZE_TINY)
            desc_text = desc_font.render(desc[:60], True, TEXT_DIM)
            r.surface.blit(desc_text, (row_rect.x + 8, row_rect.y + 26))

        # Cost
        if status:
            cost = status.current_cost.get("insight", 0)
            cost_color = GOLD if is_affordable else TEXT_DIM
            cost_text = font.render(f"{format_number(cost)} Insight", True, cost_color)
            r.surface.blit(cost_text, (row_rect.right - cost_text.get_width() - 8, row_rect.y + 6))

        self._item_rects.append((row_rect, edef.id))
        return y + 66

    def handle_event(self, event: pygame.event.Event, presenter: GamePresenter) -> str | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Sub-tabs
            for rect, idx in self._subtab_rects:
                if rect.collidepoint(event.pos):
                    self.selected_tab = idx
                    self.scroll_offset = 0
                    return None

            # Items
            for rect, elem_id in self._item_rects:
                if rect.collidepoint(event.pos):
                    if presenter.try_purchase(elem_id):
                        self._purchase_flash[elem_id] = 0.3
                    return None

        elif event.type == pygame.MOUSEWHEEL:
            self.scroll_offset = max(0, self.scroll_offset - event.y * 30)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.selected_tab = (self.selected_tab - 1) % len(self.TABS)
                self.scroll_offset = 0
            elif event.key == pygame.K_RIGHT:
                self.selected_tab = (self.selected_tab + 1) % len(self.TABS)
                self.scroll_offset = 0

        return None

    def get_interactive_rects(self) -> list[pygame.Rect]:
        rects = [r for r, _ in self._subtab_rects]
        rects.extend(r for r, _ in self._item_rects)
        return rects


# ═════════════════════════════════════════════════════════════════════
# LEXICON SCREEN — Progress and reference
# ═════════════════════════════════════════════════════════════════════

class LexiconScreen(Screen):
    """Shows translated words, root families, and stats."""

    name = "LEXICON"

    def __init__(self) -> None:
        self.scroll_offset: int = 0

    def draw(self, r: Renderer, presenter: GamePresenter, glyph_renderer: GlyphRenderer) -> None:
        y = CONTENT_TOP + 4 - self.scroll_offset
        font = get_font(FONT_SIZE_SMALL)
        font_tiny = get_font(FONT_SIZE_TINY)
        font_large = get_font(FONT_SIZE_LARGE)

        # ── Overall stats ────────────────────────────────────────────
        total_words = len(presenter.language.word_list)
        translated = presenter.total_words_translated()
        roots_discovered = sum(
            1 for root in presenter.language.root_list
            if presenter.is_root_discovered(root.id)
        )
        total_roots = len(presenter.language.root_list)

        stats_text = f"Words: {translated}/{total_words}    Roots: {roots_discovered}/{total_roots}"
        rendered = font.render(stats_text, True, WHITE)
        if y >= CONTENT_TOP - 20:
            r.surface.blit(rendered, (CONTENT_LEFT, y))
        y += LINE_HEIGHT + 4

        r.hline(CONTENT_LEFT, y, CONTENT_WIDTH)
        y += 8

        # ── Root families ────────────────────────────────────────────
        section_text = font_large.render("Root Families", True, CYAN)
        if CONTENT_TOP - 20 <= y <= CONTENT_BOTTOM:
            r.surface.blit(section_text, (CONTENT_LEFT, y))
        y += LINE_HEIGHT + 8

        for root in presenter.language.root_list:
            if y > CONTENT_BOTTOM + 100:
                break

            discovered = presenter.is_root_discovered(root.id)
            words_count = presenter.words_translated_in_root(root.id)
            total_in_root = len(root.word_ids)

            # Root header
            if discovered:
                header = f"Root: {root.display_name}  ({words_count}/{total_in_root})"
                header_color = CYAN
            else:
                header = f"??? ({words_count}/{root.discovery_threshold} to discover)"
                header_color = TEXT_DIM

            if CONTENT_TOP - 20 <= y <= CONTENT_BOTTOM:
                rendered = font.render(header, True, header_color)
                r.surface.blit(rendered, (CONTENT_LEFT + 4, y))

                # Progress bar
                progress = words_count / total_in_root
                r.progress_bar(
                    CONTENT_LEFT + 300, y + 2,
                    200, 14, progress,
                    CYAN if discovered else GRAY,
                )
            y += LINE_HEIGHT

            # Word list for this root
            if discovered:
                for wid in root.word_ids:
                    word = presenter.language.words[wid]
                    is_translated = presenter.is_word_translated(wid)

                    if CONTENT_TOP - 20 <= y <= CONTENT_BOTTOM:
                        # Glyph
                        glyph_color = GREEN if is_translated else STONE_DIM
                        glyph_surf = glyph_renderer.render_word(word, 18, glyph_color)
                        r.surface.blit(glyph_surf, (CONTENT_LEFT + 20, y + 1))

                        # Meaning (if translated)
                        if is_translated:
                            meaning = font_tiny.render(f"= {word.meaning}", True, GREEN)
                            r.surface.blit(meaning, (CONTENT_LEFT + 80, y + 2))
                        else:
                            unknown = font_tiny.render("= ???", True, TEXT_DIM)
                            r.surface.blit(unknown, (CONTENT_LEFT + 80, y + 2))

                    y += LINE_HEIGHT_SMALL

            y += 8

        # ── Translated words list ────────────────────────────────────
        y += 4
        r.hline(CONTENT_LEFT, y, CONTENT_WIDTH)
        y += 8

        section_text = font_large.render("All Translated Words", True, GREEN)
        if CONTENT_TOP - 20 <= y <= CONTENT_BOTTOM:
            r.surface.blit(section_text, (CONTENT_LEFT, y))
        y += LINE_HEIGHT + 4

        cols = 3
        col_w = CONTENT_WIDTH // cols
        col = 0
        row_y = y

        for word in presenter.language.word_list:
            if not presenter.is_word_translated(word.id):
                continue

            x = CONTENT_LEFT + col * col_w
            if CONTENT_TOP - 20 <= row_y <= CONTENT_BOTTOM:
                glyph_surf = glyph_renderer.render_word(word, 16, GREEN)
                r.surface.blit(glyph_surf, (x + 4, row_y + 1))

                meaning = font_tiny.render(word.meaning, True, GREEN)
                r.surface.blit(meaning, (x + 50, row_y + 2))

            col += 1
            if col >= cols:
                col = 0
                row_y += LINE_HEIGHT_SMALL

        if col > 0:
            row_y += LINE_HEIGHT_SMALL

    def handle_event(self, event: pygame.event.Event, presenter: GamePresenter) -> str | None:
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_offset = max(0, self.scroll_offset - event.y * 30)
        return None
