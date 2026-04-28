"""Pygame renderer helper for micromate."""
import math
import os
import io
import sys
import traceback
import pygame
from pathlib import Path

ADV_BAR_W = 20  # pixels reserved on the right for the advantage bar

_DEBUG_ASSETS = os.environ.get("MICROMATE_DEBUG_ASSETS") == "1"

try:
    import cairosvg
    from PIL import Image
except (ImportError, OSError):
    cairosvg = None
    Image = None

_PKG_DIR = os.path.dirname(__file__)
_CANDIDATE_SVG_DIRS = [
    os.path.join(_PKG_DIR, 'assets', 'svg'),
    os.path.join(_PKG_DIR, '..', '..', 'assets', 'svg'),
]
_CANDIDATE_PNG_DIRS = [
    os.path.join(_PKG_DIR, 'assets', 'png'),
    os.path.join(_PKG_DIR, '..', '..', 'assets', 'png'),
]
ASSETS_SVG = next((p for p in _CANDIDATE_SVG_DIRS if os.path.isdir(p)), _CANDIDATE_SVG_DIRS[0])
ASSETS_PNG = next((p for p in _CANDIDATE_PNG_DIRS if os.path.isdir(p)), _CANDIDATE_PNG_DIRS[0])
THEMES = (
    {
        "name": "Classic",
        "background": (24, 24, 28),
        "light_square": (240, 217, 181),
        "dark_square": (181, 136, 99),
        "from_highlight": (244, 208, 63),
        "to_highlight": (88, 214, 141),
        "check_highlight": (220, 80, 80),
        "selected_highlight": (100, 149, 237),
        "cursor_highlight": (200, 200, 200),
        "panel_fill": (18, 20, 24),
        "panel_border": (72, 78, 88),
        "text": (240, 240, 240),
        "subtext": (210, 210, 210),
    },
    {
        "name": "Forest",
        "background": (18, 28, 21),
        "light_square": (219, 236, 204),
        "dark_square": (102, 138, 92),
        "from_highlight": (246, 221, 110),
        "to_highlight": (102, 255, 163),
        "check_highlight": (255, 100, 80),
        "selected_highlight": (80, 160, 220),
        "cursor_highlight": (180, 220, 180),
        "panel_fill": (17, 41, 26),
        "panel_border": (108, 150, 101),
        "text": (237, 244, 231),
        "subtext": (197, 221, 190),
    },
    {
        "name": "Midnight",
        "background": (12, 16, 28),
        "light_square": (137, 173, 212),
        "dark_square": (54, 74, 108),
        "from_highlight": (255, 210, 79),
        "to_highlight": (94, 234, 212),
        "check_highlight": (255, 80, 100),
        "selected_highlight": (120, 160, 255),
        "cursor_highlight": (180, 200, 240),
        "panel_fill": (17, 25, 42),
        "panel_border": (98, 123, 166),
        "text": (239, 244, 255),
        "subtext": (190, 204, 233),
    },
    {
        "name": "Grey",
        "background": (40, 42, 46),
        "light_square": (200, 200, 200),
        "dark_square": (110, 112, 116),
        "from_highlight": (220, 200, 120),
        "to_highlight": (160, 200, 170),
        "check_highlight": (220, 100, 100),
        "selected_highlight": (130, 160, 200),
        "cursor_highlight": (210, 210, 210),
        "panel_fill": (30, 32, 36),
        "panel_border": (110, 112, 118),
        "text": (235, 235, 235),
        "subtext": (190, 192, 196),
    },
    {
        "name": "Rosewood",
        "background": (34, 22, 24),
        "light_square": (232, 201, 188),
        "dark_square": (132, 82, 74),
        "from_highlight": (250, 201, 80),
        "to_highlight": (111, 233, 164),
        "check_highlight": (240, 100, 90),
        "selected_highlight": (180, 120, 200),
        "cursor_highlight": (230, 200, 190),
        "panel_fill": (48, 30, 32),
        "panel_border": (162, 113, 104),
        "text": (247, 236, 232),
        "subtext": (223, 194, 187),
    },
)
DEFAULT_THEME_INDEX = 0

def get_theme(theme_index):
    return THEMES[theme_index % len(THEMES)]

_font_cache: dict = {}

def _get_font(size, bold=False):
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    if not pygame.font.get_init():
        try:
            pygame.font.init()
        except (pygame.error, ImportError, RuntimeError):
            return None
    font = None
    try:
        font = pygame.font.SysFont(None, size, bold=bold)
    except (pygame.error, OSError, ImportError, NotImplementedError, RuntimeError):
        pass
    if font is None:
        try:
            font = pygame.font.Font(None, size)
        except (pygame.error, OSError, ImportError, NotImplementedError, RuntimeError):
            pass
    _font_cache[key] = font
    return font

_warned = set()

def _warn_once(key, msg):
    if key in _warned:
        return
    _warned.add(key)
    print(f"micro-mate: {msg}", file=sys.stderr)
    if _DEBUG_ASSETS:
        traceback.print_exc()

def _render_svg_to_surface(svg_path, width, height):
    """Render SVG to pygame surface at specified size using cairosvg."""
    if cairosvg is None or Image is None:
        if _DEBUG_ASSETS:
            _warn_once("svg-deps", "cairosvg/Pillow not importable; skipping SVG pieces")
        return None

    try:
        png_bytes = io.BytesIO()
        cairosvg.svg2png(
            url=str(svg_path),
            write_to=png_bytes,
            output_width=width,
            output_height=height,
        )
        png_bytes.seek(0)

        pil_img = Image.open(png_bytes).convert("RGBA")
        pygame_surface = pygame.image.fromstring(
            pil_img.tobytes("raw", "RGBA"),
            pil_img.size,
            "RGBA"
        )
        try:
            return pygame_surface.convert_alpha()
        except pygame.error:
            return pygame_surface
    except Exception as e:
        _warn_once("svg-render", f"SVG render failed ({type(e).__name__}: {e}); falling back to PNG")
        return None

def load_piece_surfaces():
    """Scan for SVG pieces. Returns empty dict; rendering happens at draw time."""
    return {}

def get_piece_surface(piece_key, size, cache={}):
    """Get or render a piece surface at the specified size. SVG preferred, PNG fallback."""
    cache_key = (piece_key, size)
    if cache_key in cache:
        return cache[cache_key]

    surface = None

    # Try SVG first (best quality at any size)
    if os.path.isdir(ASSETS_SVG):
        svg_path = os.path.join(ASSETS_SVG, f"{piece_key}.svg")
        if os.path.isfile(svg_path):
            surface = _render_svg_to_surface(svg_path, size, size)

    # Fall back to bundled PNG (works without system libcairo)
    if surface is None:
        if not os.path.isdir(ASSETS_PNG):
            _warn_once("png-dir", f"PNG asset dir missing: {ASSETS_PNG} (reinstall: pipx install --force ~/Projects/micro-mate)")
        else:
            png_path = os.path.join(ASSETS_PNG, f"{piece_key}.png")
            if not os.path.isfile(png_path):
                _warn_once(f"png-missing-{piece_key}", f"PNG missing: {png_path}")
            else:
                try:
                    img = pygame.image.load(png_path)
                    try:
                        img = img.convert_alpha()
                    except pygame.error:
                        pass
                    surface = pygame.transform.smoothscale(img, (size, size))
                except Exception as e:
                    _warn_once(f"png-load-{piece_key}", f"PNG load failed for {png_path} ({type(e).__name__}: {e})")

    if surface:
        cache[cache_key] = surface
    return surface

def coord_border(screen_size, show_coords):
    """Pixel width reserved on each edge for the coordinate band."""
    if not show_coords:
        return 0
    return max(18, min(screen_size) // 28)

def board_geometry(screen_size, board, show_coords=False, right_panel=0):
    """Return (cell, x0, y0) — single source of truth for board layout.

    right_panel reserves that many pixels on the right side of the window
    (e.g. for the advantage bar) and keeps the board in the remaining area.
    """
    w, h = screen_size
    border = coord_border(screen_size, show_coords)
    inner_w = max(1, w - 2 * border - right_panel)
    inner_h = max(1, h - 2 * border)
    cell = min(inner_w // board.cols, inner_h // board.rows)
    board_w = cell * board.cols
    board_h = cell * board.rows
    x0 = border + (inner_w - board_w) // 2
    y0 = (h - board_h) // 2
    return cell, x0, y0

def pixel_to_square(screen_size, board, px, py, show_coords=False, right_panel=0):
    """Convert screen pixel to board (row, col). Returns None if outside board."""
    cell, x0, y0 = board_geometry(screen_size, board, show_coords=show_coords,
                                  right_panel=right_panel)
    col = (px - x0) // cell
    row = (py - y0) // cell
    if 0 <= row < board.rows and 0 <= col < board.cols:
        return (row, col)
    return None

_label_cache: dict = {}

def _draw_coord_labels(screen, board, theme, cell, x0, y0, border):
    label_color = theme["subtext"]
    font = _get_font(max(12, int(border * 0.7)), bold=True)
    if font is None:
        return
    rows, cols = board.rows, board.cols
    for c in range(cols):
        letter = chr(ord('a') + c)
        lkey = (letter, font.size(letter)[1], label_color)
        label = _label_cache.get(lkey) or _label_cache.setdefault(lkey, font.render(letter, True, label_color))
        cx = x0 + c * cell + cell // 2
        top_y = max(0, y0 - border // 2)
        bot_y = y0 + rows * cell + border // 2
        screen.blit(label, label.get_rect(center=(cx, top_y)))
        screen.blit(label, label.get_rect(center=(cx, bot_y)))
    for r in range(rows):
        number = str(rows - r)
        lkey = (number, font.size(number)[1], label_color)
        label = _label_cache.get(lkey) or _label_cache.setdefault(lkey, font.render(number, True, label_color))
        cy = y0 + r * cell + cell // 2
        left_x = max(0, x0 - border // 2)
        right_x = x0 + cols * cell + border // 2
        screen.blit(label, label.get_rect(center=(left_x, cy)))
        screen.blit(label, label.get_rect(center=(right_x, cy)))

def _draw_piece_fallback(screen, rect, piece, cell):
    fill = (242, 242, 236) if piece.color == "w" else (32, 32, 36)
    outline = (28, 28, 28) if piece.color == "w" else (235, 235, 235)
    text_color = (24, 24, 24) if piece.color == "w" else (244, 244, 244)
    center = rect.center
    radius = max(8, cell // 2 - 10)

    pygame.draw.circle(screen, fill, center, radius)
    pygame.draw.circle(screen, outline, center, radius, max(2, cell // 24))

    font = _get_font(max(18, int(cell * 0.5)), bold=True)
    if font is not None:
        label = font.render(piece.kind, True, text_color)
        label_rect = label.get_rect(center=center)
        screen.blit(label, label_rect)
    else:
        marker_width = max(6, cell // 6)
        marker_height = max(4, cell // 16)
        marker_rect = pygame.Rect(0, 0, marker_width, marker_height)
        marker_rect.center = center
        pygame.draw.rect(screen, text_color, marker_rect, border_radius=max(2, marker_height // 2))

def draw_board(screen, board, piece_surfaces=None, last_move=None, theme_index=DEFAULT_THEME_INDEX, padding=8,
               selected_sq=None, cursor_sq=None, current_turn=None, show_coords=False, king_in_check_sq=None,
               right_panel=0):
    rows, cols = board.rows, board.cols
    cell, x0, y0 = board_geometry(screen.get_size(), board, show_coords=show_coords,
                                  right_panel=right_panel)
    theme = get_theme(theme_index)
    border = coord_border(screen.get_size(), show_coords)
    colors = [theme["light_square"], theme["dark_square"]]
    for r in range(rows):
        for c in range(cols):
            rect = pygame.Rect(x0 + c*cell, y0 + r*cell, cell, cell)
            color = colors[(r+c)%2]
            pygame.draw.rect(screen, color, rect)
            piece = board.piece_at(r, c)
            if piece:
                key = f"{piece.color}_{piece.kind.lower()}"
                target_size = max(1, cell - padding)
                surf = get_piece_surface(key, target_size)
                if surf:
                    blit_x = rect.x + (rect.w - target_size) // 2
                    blit_y = rect.y + (rect.h - target_size) // 2
                    screen.blit(surf, (blit_x, blit_y))
                else:
                    _draw_piece_fallback(screen, rect, piece, cell)

    # Draw check indicator (red border around king in check)
    if king_in_check_sq is not None:
        row, col = king_in_check_sq
        rect = pygame.Rect(x0 + col * cell, y0 + row * cell, cell, cell)
        line_width = max(4, cell // 12)
        pygame.draw.rect(screen, theme["check_highlight"], rect, line_width)

    # Draw selected square highlight (blue border)
    if selected_sq is not None:
        row, col = selected_sq
        rect = pygame.Rect(x0 + col * cell, y0 + row * cell, cell, cell)
        line_width = max(4, cell // 12)
        pygame.draw.rect(screen, theme["selected_highlight"], rect, line_width)

    # Draw keyboard cursor highlight (only when not same as selected)
    if cursor_sq is not None and cursor_sq != selected_sq:
        row, col = cursor_sq
        rect = pygame.Rect(x0 + col * cell, y0 + row * cell, cell, cell)
        line_width = max(3, cell // 16)
        pygame.draw.rect(screen, theme["cursor_highlight"], rect, line_width)

    if last_move:
        line_width = max(3, cell // 16)
        base = theme["from_highlight"] if current_turn == 'b' else theme["to_highlight"]
        # Vary brightness in HSV space so saturation stays high.
        base_color = pygame.Color(int(base[0]), int(base[1]), int(base[2]))
        h, s, v, _ = base_color.hsva
        s = min(100.0, s * 1.4 + 15.0)
        from_hsv = pygame.Color(0)
        from_hsv.hsva = (h, s, max(0.0, v * 0.65), 100)
        to_hsv = pygame.Color(0)
        to_hsv.hsva = (h, s, min(100.0, v * 1.05 + 5.0), 100)
        from_row, from_col = last_move.from_sq
        to_row, to_col = last_move.to_sq
        from_rect = pygame.Rect(x0 + from_col * cell, y0 + from_row * cell, cell, cell)
        to_rect = pygame.Rect(x0 + to_col * cell, y0 + to_row * cell, cell, cell)
        pygame.draw.rect(screen, from_hsv, from_rect, line_width)
        pygame.draw.rect(screen, to_hsv, to_rect, line_width)

    if show_coords and border > 0:
        _draw_coord_labels(screen, board, theme, cell, x0, y0, border)


def draw_advantage_bar(screen, eval_score, board, theme_index, show_coords,
                       right_panel=ADV_BAR_W):
    """Draw a vertical win-probability bar in the right panel strip."""
    if right_panel <= 0:
        return
    cell, x0, y0 = board_geometry(screen.get_size(), board, show_coords, right_panel)
    board_h = cell * board.rows

    # Sigmoid over capped eval (±2000 cp) so dice-mode extreme values stay sane
    capped = max(-2000.0, min(2000.0, float(eval_score)))
    p_white = 1.0 / (1.0 + math.exp(-capped / 400.0))

    theme = get_theme(theme_index)
    gap = 4
    bar_x = x0 + cell * board.cols + gap
    bar_y = y0
    bar_w = screen.get_width() - bar_x - 2
    bar_h = board_h

    if bar_w <= 0 or bar_h <= 0:
        return

    white_h = max(0, min(bar_h, int(bar_h * p_white)))
    black_h = bar_h - white_h

    dark  = (28, 28, 28)
    light = (218, 218, 212)

    if black_h > 0:
        pygame.draw.rect(screen, dark,  (bar_x, bar_y, bar_w, black_h))
    if white_h > 0:
        pygame.draw.rect(screen, light, (bar_x, bar_y + black_h, bar_w, white_h))

    # Border
    pygame.draw.rect(screen, theme["panel_border"], (bar_x, bar_y, bar_w, bar_h), 1)

    # Percentage labels if there is enough vertical room in each section
    font = _get_font(max(9, min(bar_w - 2, 12)), bold=False)
    if font and bar_h >= 60:
        pct_w = int(p_white * 100)
        pct_b = 100 - pct_w
        # White label (bottom section)
        if white_h >= 16:
            lbl = font.render(str(pct_w), True, dark)
            screen.blit(lbl, lbl.get_rect(center=(bar_x + bar_w // 2,
                                                   bar_y + black_h + white_h // 2)))
        # Black label (top section)
        if black_h >= 16:
            lbl = font.render(str(pct_b), True, light)
            screen.blit(lbl, lbl.get_rect(center=(bar_x + bar_w // 2,
                                                   bar_y + black_h // 2)))
