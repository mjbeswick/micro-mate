#!/usr/bin/env python3
"""Generate screenshots of micro-mate for the README.
Run with the pipx venv Python that has cairosvg:
    ~/.local/pipx/venvs/micro-mate/bin/python3 tools/generate_screenshots.py
"""
import os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
pygame.init()
pygame.font.init()

from micromate.engine import Game
from micromate.renderer import (
    THEMES, get_theme, draw_board, board_geometry, coord_border,
    get_piece_surface, _get_font,
)

OUT = os.path.join(os.path.dirname(__file__), '..', 'screenshots')
os.makedirs(OUT, exist_ok=True)

# ── helpers ──────────────────────────────────────────────────────────────────

def make_screen(size=600):
    s = pygame.Surface((size, size))
    return s

def render(surf, game, theme_idx, show_coords=True, last_move=None,
           selected_sq=None, king_in_check_sq=None):
    theme = get_theme(theme_idx)
    surf.fill(theme["background"])
    draw_board(surf, game.board, piece_surfaces=None,
               last_move=last_move,
               selected_sq=selected_sq,
               king_in_check_sq=king_in_check_sq,
               theme_index=theme_idx,
               show_coords=show_coords)

def save(surf, name):
    path = os.path.join(OUT, name)
    pygame.image.save(surf, path)
    print(f"  saved {name}")

# ── modal drawing ─────────────────────────────────────────────────────────────

def draw_blur_overlay(surf):
    w, h = surf.get_size()
    ov = pygame.Surface((w, h))
    ov.set_alpha(130)
    ov.fill((0, 0, 0))
    surf.blit(ov, (0, 0))

def draw_modal(surf, title, rows, theme_idx, width=None, highlight_row=None):
    """Draw a fake thorpy-style modal over surf."""
    theme = get_theme(theme_idx)
    w, h = surf.get_size()

    PADDING = 18
    ROW_H = max(22, h // 28)
    TITLE_H = ROW_H + 8
    modal_w = width or min(320, int(w * 0.6))
    modal_h = TITLE_H + len(rows) * ROW_H + PADDING * 2 + 8

    mx = (w - modal_w) // 2
    my = (h - modal_h) // 2

    border_col = theme["panel_border"]
    fill_col = theme["panel_fill"]
    text_col = theme["text"]
    sub_col = theme["subtext"]
    hl_col = theme["from_highlight"]

    # Shadow
    shadow = pygame.Surface((modal_w + 8, modal_h + 8))
    shadow.set_alpha(80)
    shadow.fill((0, 0, 0))
    surf.blit(shadow, (mx + 4, my + 4))

    # Body
    pygame.draw.rect(surf, fill_col, (mx, my, modal_w, modal_h), border_radius=8)
    pygame.draw.rect(surf, border_col, (mx, my, modal_w, modal_h), 2, border_radius=8)

    # Title bar
    pygame.draw.rect(surf, border_col,
                     (mx, my, modal_w, TITLE_H), border_radius=8)

    title_font = _get_font(max(14, ROW_H - 2), bold=True)
    row_font   = _get_font(max(12, ROW_H - 6))
    btn_font   = _get_font(max(12, ROW_H - 4), bold=True)

    def blit_text(font, text, color, cx, cy):
        if font is None:
            return
        surf2 = font.render(text, True, color)
        r = surf2.get_rect(center=(cx, cy))
        surf.blit(surf2, r)

    blit_text(title_font, title, text_col, mx + modal_w // 2, my + TITLE_H // 2)

    y = my + TITLE_H + PADDING
    for i, row in enumerate(rows):
        cy = y + ROW_H // 2
        is_btn  = row.get("btn", False)
        is_sel  = row.get("selected", False)
        label   = row.get("label", "")
        value   = row.get("value", "")

        if is_btn:
            btn_w = modal_w - PADDING * 2
            btn_h = ROW_H + 2
            bx = mx + PADDING
            by = y - 2
            # Button colors with highlight
            bc = theme["from_highlight"] if row.get("primary") else border_col
            tc = (30, 30, 30) if row.get("primary") else text_col
            pygame.draw.rect(surf, bc, (bx, by, btn_w, btn_h), border_radius=5)
            pygame.draw.rect(surf, border_col, (bx, by, btn_w, btn_h), 1, border_radius=5)
            blit_text(btn_font, label, tc, mx + modal_w // 2, cy)
        elif label and value:
            # Key + value pair  (setting row)
            blit_text(row_font, label, sub_col, mx + PADDING + modal_w // 4, cy)
            # Value pill
            if is_sel:
                pill_w = max(70, len(value) * 8 + 16)
                pill_x = mx + modal_w // 2 + 10
                pill_y = y + 2
                pill_h = ROW_H - 4
                pygame.draw.rect(surf, hl_col,
                                 (pill_x, pill_y, pill_w, pill_h), border_radius=4)
                blit_text(row_font, value, (30, 30, 30), pill_x + pill_w // 2, cy)
            else:
                blit_text(row_font, value, text_col, mx + modal_w * 3 // 4, cy)
        elif label:
            blit_text(row_font, label, text_col, mx + modal_w // 2, cy)
        y += ROW_H

# ── SCENE 1: Classic theme, 8×8, coords, mid-game ───────────────────────────
print("Generating board screenshots…")
SIZE = 600

for theme_idx, theme in enumerate(THEMES):
    s = make_screen(SIZE)
    g = Game(rows=8, cols=8)
    render(s, g, theme_idx, show_coords=True)
    save(s, f"theme_{theme['name'].lower()}.png")

# 10×10 and 16×16 boards
for rows, cols in [(10, 10), (16, 16)]:
    s = make_screen(SIZE)
    g = Game(rows=rows, cols=cols)
    render(s, g, 0, show_coords=True)
    save(s, f"board_{rows}x{cols}.png")

# ── SCENE 2: New Game modal ──────────────────────────────────────────────────
print("Generating modal screenshots…")

def screenshot_new_game_modal(theme_idx, filename):
    s = make_screen(SIZE)
    g = Game(rows=8, cols=8)
    render(s, g, theme_idx, show_coords=True)
    draw_blur_overlay(s)

    modal_rows = [
        {"label": "Board size",  "value": "8x8",          "selected": True},
        {"label": "AI strength", "value": "L3 normal",    "selected": False},
        {"label": "Game mode",   "value": "Human vs AI",  "selected": False},
        {"label": "Your color",  "value": "White",        "selected": False},
        {"label": "Coordinates", "value": "Yes",          "selected": False},
        {},  # spacer
        {"label": "Quit",  "btn": True, "primary": False},
        {"label": "Start", "btn": True, "primary": True},
    ]
    draw_modal(s, "New Game", modal_rows, theme_idx, width=280)
    save(s, filename)

screenshot_new_game_modal(0, "modal_new_game_classic.png")
screenshot_new_game_modal(2, "modal_new_game_midnight.png")

# ── SCENE 3: Checkmate modal ─────────────────────────────────────────────────
def screenshot_checkmate_modal(theme_idx, filename):
    s = make_screen(SIZE)
    g = Game(rows=8, cols=8)
    render(s, g, theme_idx, show_coords=True)
    draw_blur_overlay(s)

    modal_rows = [
        {"label": "White wins!"},
        {"label": "Black is checkmated."},
        {},
        {"label": "OK", "btn": True, "primary": True},
    ]
    draw_modal(s, "Checkmate", modal_rows, theme_idx, width=240)
    save(s, filename)

screenshot_checkmate_modal(0, "modal_checkmate_classic.png")

print("Done.")
