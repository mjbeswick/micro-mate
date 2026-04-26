"""Entry point for Micro-Mate."""
import argparse
import json
import re
import sys
import threading
from pathlib import Path
import os
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame
# thorpy is imported after pygame.init() in main() because it creates system
# cursors at module-import time, which requires an active display on Linux.
tp = None  # populated in main()

if __package__ == "src":
    from .micromate.engine import AI, Game, Move
    from .micromate.pgn import export_pgn, import_pgn, is_pgn_compatible
    from .micromate.renderer import (
        DEFAULT_THEME_INDEX,
        THEMES,
        get_theme,
        _get_font,
        load_piece_surfaces,
        draw_board,
        pixel_to_square,
    )
else:
    from micromate.engine import AI, Game, Move
    from micromate.pgn import export_pgn, import_pgn, is_pgn_compatible
    from micromate.renderer import (
        DEFAULT_THEME_INDEX,
        THEMES,
        get_theme,
        _get_font,
        load_piece_surfaces,
        draw_board,
        pixel_to_square,
    )

SAVE_PATH = Path.home() / ".micro-mate" / "save-state.json"
OPTIONS_PATH = Path.home() / ".micro-mate" / "options.json"
BOARD_SIZES = [(3, 3), (4, 4), (6, 6), (8, 8), (10, 10), (16, 16)]
DEFAULT_BOARD_SIZE = (8, 8)
MIN_AI_DEPTH = 1
MAX_AI_DEPTH = 5
DEFAULT_AI_DEPTH = 3

# Mutable globals controlled by CLI / in-app keys.
_options = {
    "ai_enabled": True,
    "ai_depth": DEFAULT_AI_DEPTH,
    "show_coords": True,
    "game_mode": "Human vs AI",
    "player_color": "White"
}
_toast = {"text": None, "until": 0}

def _apply_thorpy_theme(theme_index):
    """Apply thorpy theme_game1 with colors from the chess theme."""
    t = get_theme(theme_index)
    tp.theme_game1(color1=t["panel_fill"],
                   color2=t["from_highlight"],
                   color3=t["text"])

def _configure_thorpy_for_modal(screen, theme_index):
    """Scale thorpy font to window size then rebuild element styles."""
    w, h = screen.get_size()
    font_size = max(11, min(min(w, h) // 40, 18))
    tp.set_default_font("arial", font_size)
    _apply_thorpy_theme(theme_index)

def _make_modal_transparent(modal):
    """Set modal background to semi-transparent."""
    if hasattr(modal, 'surface') and modal.surface is not None:
        modal.surface.set_alpha(200)  # 200/255 = ~78% opaque
    return modal

def _blur_screen(screen, radius=5):
    """Create a blurred overlay effect by drawing semi-transparent darker surface."""
    # Simple blur effect: create a darkened, semi-transparent overlay
    # This is faster than actual blurring and gives a modal-focusing effect
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h))
    overlay.set_alpha(120)  # Semi-transparent
    overlay.fill((0, 0, 0))  # Dark overlay
    return overlay

def _set_toast(text, ms=1100):
    _toast["text"] = text
    _toast["until"] = pygame.time.get_ticks() + ms

def print_board_notation(game):
    """Print board notation before exit."""
    try:
        from micromate.pgn import export_pgn
        pgn = export_pgn(game)
        if pgn:
            print("\n--- Final Position (PGN) ---")
            print(pgn)
        else:
            print("\n--- Final Position (non-8x8 board, PGN export unavailable) ---")
            print(f"Board: {game.board.rows}x{game.board.cols}")
            print(f"Moves: {len(game.move_history)}")
            if game.move_history:
                last_move = game.move_history[-1]
                print(f"Last move: {last_move}")
    except Exception:
        pass

def create_game_with_size(rows, cols):
    """Create a new game with specified board size."""
    return Game(rows=rows, cols=cols, ai_depth=_options["ai_depth"])

def show_help_modal(screen, game, theme_index, selected_sq=None):
    """Display help modal with shortcuts using thorpy (default colors)."""
    from thorpy.elements import TitleBox, Text, Group
    _configure_thorpy_for_modal(screen, theme_index)
    
    # Compact shortcut list with proper alignment
    shortcuts = [
        ("Click", "Select/move"),
        ("Space/Arrows", "Move/select"),
        ("Esc", "Deselect"),
        ("[/]", "Step history"),
        ("R", "Restart"),
        ("N", "New game"),
        ("T", "Cycle theme"),
        ("+/-", "AI strength"),
        ("P", "Print PGN"),
        ("C", "Coords"),
        ("?", "Close help"),
    ]
    
    # Create two-column layout for better alignment
    text_lines = ["Shortcuts:"]
    max_key_len = max(len(key) for key, _ in shortcuts)
    for key, desc in shortcuts:
        # Pad keys with spaces for visual alignment
        padded_key = key.ljust(max_key_len + 2)
        text_lines.append(f"{padded_key}{desc}")
    
    help_text = "\n".join(text_lines)
    text_elem = Text(help_text)
    
    # Create modal with size constraints to fit on screen
    w, h = screen.get_size()
    max_width = min(480, int(w * 0.75))
    max_height = min(420, int(h * 0.8))
    
    box = TitleBox("Help", children=[text_elem], scrollbar_if_needed=True, 
                   size_limit=(max_width, max_height))
    box.center_on(screen)
    _make_modal_transparent(box)
    
    _last_size = [screen.get_size()]
    def draw_bg():
        _draw_background_for_modal(screen, game, theme_index)
        if screen.get_size() != _last_size[0]:
            _last_size[0] = screen.get_size()
            box.center_on(screen)
    
    box.launch_alone(draw_bg, click_outside_cancel=True)

def _draw_background_for_modal(screen, game, theme_index):
    """Draw board with blur overlay when modal is shown."""
    if game is not None:
        # Draw the game board
        from micromate.renderer import draw_board as render_board
        render_board(
            screen,
            game.board,
            theme_index=theme_index,
            show_coords=_options["show_coords"],
        )
    # Draw blur overlay on top
    overlay = _blur_screen(screen)
    if overlay:
        screen.blit(overlay, (0, 0))

def _strength_label(depth):
    return {1: "casual", 2: "easy", 3: "normal", 4: "strong", 5: "tough"}.get(depth, "")

def show_new_game_modal(screen, theme_index, allow_cancel=False,
                        current_size=None, current_depth=None, piece_surfaces=None):
    """Pick board size, AI strength, game mode, and color via thorpy. Returns (rows, cols, depth, mode, color) or None."""
    from thorpy.elements import TitleBox, TogglablesPool, Button, Group, Text, Box
    from micromate.engine import Game
    _configure_thorpy_for_modal(screen, theme_index)
    
    sizes = list(BOARD_SIZES)
    depths = list(range(MIN_AI_DEPTH, MAX_AI_DEPTH + 1))
    modes = ["Human vs AI", "Human vs Human"]
    colors = ["White", "Black"]
    
    size_labels = [f"{r}x{c}" for (r, c) in sizes]
    depth_labels = [f"L{d} {_strength_label(d)}" for d in depths]
    
    size_idx = sizes.index(current_size) if current_size in sizes else sizes.index(DEFAULT_BOARD_SIZE)
    depth_idx = depths.index(current_depth) if current_depth in depths else depths.index(DEFAULT_AI_DEPTH)
    
    result = {"value": None}
    
    # Create a preview game with the current selected size
    preview_game = Game(rows=sizes[size_idx][0], cols=sizes[size_idx][1])
    preview_state = {"game": preview_game}
    
    # Labels with keyboard hints
    size_label = Text("Board size")
    size_pool = TogglablesPool("", choices=size_labels, initial_value=size_idx)
    size_group = Group([size_label, size_pool], "v")
    
    depth_label = Text("AI strength")
    depth_pool = TogglablesPool("", choices=depth_labels, initial_value=depth_idx)
    depth_group = Group([depth_label, depth_pool], "v")
    
    mode_label = Text("Game mode")
    mode_pool = TogglablesPool("", choices=modes, initial_value=0)
    mode_group = Group([mode_label, mode_pool], "v")
    
    color_label = Text("Your color")
    color_pool = TogglablesPool("", choices=colors, initial_value=0)
    color_group = Group([color_label, color_pool], "v")
    
    coords_label = Text("Show coordinates")
    coords_choices = ["Yes", "No"]
    coords_initial = 0 if _options["show_coords"] else 1
    coords_pool = TogglablesPool("", choices=coords_choices, initial_value=coords_initial)
    coords_group = Group([coords_label, coords_pool], "v")
    
    def on_start():
        size_val = size_pool.get_value()
        depth_val = depth_pool.get_value()
        mode_val = mode_pool.get_value()
        color_val = color_pool.get_value()
        coords_val = coords_pool.get_value()
        
        # Handle both index and string returns
        if isinstance(size_val, str):
            size_idx_val = size_labels.index(size_val)
        else:
            size_idx_val = size_val
        if isinstance(depth_val, str):
            depth_idx_val = depth_labels.index(depth_val)
        else:
            depth_idx_val = depth_val
        if isinstance(mode_val, str):
            mode_idx_val = modes.index(mode_val)
        else:
            mode_idx_val = mode_val
        if isinstance(color_val, str):
            color_idx_val = colors.index(color_val)
        else:
            color_idx_val = color_val
        if isinstance(coords_val, str):
            coords_enabled = coords_val == "Yes"
        else:
            coords_enabled = coords_val == 0
        
        result["value"] = (
            sizes[size_idx_val][0],
            sizes[size_idx_val][1],
            depths[depth_idx_val],
            modes[mode_idx_val],
            colors[color_idx_val],
            coords_enabled
        )
        tp.loops.quit_current_loop()
    
    def on_cancel():
        result["value"] = "quit"
        tp.loops.quit_current_loop()
    
    start_btn = Button("Start")
    start_btn.at_unclick = on_start
    
    cancel_btn = Button("Quit") if allow_cancel else None
    if cancel_btn:
        cancel_btn.at_unclick = on_cancel
        buttons = Group([cancel_btn, start_btn], "h")
    else:
        buttons = Group([start_btn], "h")
    
    # Add a spacer above buttons for visual separation
    spacer = Text("")
    
    elements = [
        size_group,
        depth_group,
        mode_group,
        color_group,
        coords_group,
        spacer,
        buttons
    ]
    w, h = screen.get_size()
    box = TitleBox("New Game", children=elements,
                   size_limit=(int(w * 0.88), int(h * 0.88)),
                   scrollbar_if_needed=True)
    box.center_on(screen)
    _make_modal_transparent(box)
    _last_size = [screen.get_size()]
    
    def draw_board_preview():
        """Redraw board with current selection before modal update."""
        try:
            # Draw blur overlay behind modal
            _draw_background_for_modal(screen, None, theme_index)

            if screen.get_size() != _last_size[0]:
                _last_size[0] = screen.get_size()
                box.center_on(screen)

            # Check if size selection changed
            size_val = size_pool.get_value()
            if isinstance(size_val, str):
                if size_val in size_labels:
                    size_idx_val = size_labels.index(size_val)
                else:
                    size_idx_val = size_idx  # fallback to initial
            else:
                size_idx_val = size_val
            
            # Ensure index is valid
            if size_idx_val >= len(sizes):
                size_idx_val = size_idx
            
            selected_rows, selected_cols = sizes[size_idx_val]
            if (preview_state["game"].board.rows != selected_rows or 
                preview_state["game"].board.cols != selected_cols):
                preview_state["game"] = Game(rows=selected_rows, cols=selected_cols)
            
            # Draw the board
            theme = get_theme(theme_index)
            coords_val = coords_pool.get_value()
            show_coords_preview = (coords_val == "Yes") if isinstance(coords_val, str) else (coords_val == 0)
            draw_board(
                screen,
                preview_state["game"].board,
                piece_surfaces=piece_surfaces,
                theme_index=theme_index,
                show_coords=show_coords_preview,
            )
        except Exception as e:
            # Silently handle errors in preview to not crash the modal
            pass
    
    box.launch_alone(func_before=draw_board_preview, click_outside_cancel=allow_cancel)
    
    return result["value"]

def show_checkmate_modal(screen, theme_index, loser_color):
    """Display checkmate modal announcing the winner."""
    from thorpy.elements import TitleBox, Text, Button, Group
    _configure_thorpy_for_modal(screen, theme_index)
    
    winner = "White" if loser_color == 'b' else "Black"
    loser = "Black" if loser_color == 'b' else "White"
    message = f"{winner} wins!\n{loser} is checkmated."
    
    msg_text = Text(message)
    ok_btn = Button("OK")
    
    def on_ok():
        tp.loops.quit_current_loop()
    
    ok_btn.at_unclick = on_ok
    
    elements = [msg_text, ok_btn]
    box = TitleBox("Checkmate", children=elements)
    box.center_on(screen)
    _make_modal_transparent(box)

    _last_size = [screen.get_size()]
    def draw_bg():
        _draw_background_for_modal(screen, None, theme_index)
        if screen.get_size() != _last_size[0]:
            _last_size[0] = screen.get_size()
            box.center_on(screen)
    
    box.launch_alone(func_before=draw_bg, click_outside_cancel=False)

HUMAN_COLOR = 'w'

def _movable_squares(game):
    """Set of from-squares the current player can move from this turn."""
    return {m.from_sq for m in game.get_legal_moves()}

def _legal_targets(game, from_sq):
    """Squares the piece on from_sq can legally move to (plus from_sq itself for deselect)."""
    if from_sq is None:
        return set()
    targets = {m.to_sq for m in game.get_legal_moves() if m.from_sq == from_sq}
    targets.add(from_sq)
    return targets

def _next_in_set(game, current, dr, dc, allowed):
    """Walk (dr, dc) wrapping until landing on a square in `allowed`."""
    if not allowed:
        return current
    rows, cols = game.board.rows, game.board.cols
    cr, cc = current if current is not None else (rows - 1, 0)
    for _ in range(rows * cols):
        cr = (cr + dr) % rows
        cc = (cc + dc) % cols
        if (cr, cc) in allowed:
            return (cr, cc)
    return current

def _initial_cursor(game):
    """First movable square (top-left scan), or fallback corner."""
    movable = _movable_squares(game)
    if not movable:
        return (game.board.rows - 1, 0)
    return min(movable)

def _fit_window_to_board(screen, base_size, board):
    """Resize the display so it tightly fits the board (no letterboxing)."""
    border_each = max(18, base_size // 28) if _options["show_coords"] else 0
    inner = max(80, base_size - 2 * border_each)
    cell = max(40, min(inner // board.cols, inner // board.rows))
    target = (cell * board.cols + 2 * border_each, cell * board.rows + 2 * border_each)
    if screen.get_size() != target:
        screen = pygame.display.set_mode(target, pygame.RESIZABLE)
    return screen, target

def apply_ai_move_if_needed(game, screen=None, theme_index=DEFAULT_THEME_INDEX):
    """If it's the AI's turn and the game isn't over, play its move.

    When `screen` is provided the search runs in a worker thread and a
    'Thinking...' modal with a Force move button is shown. Without a
    screen the call is synchronous (used at startup before the loop)."""
    if not _options["ai_enabled"]:
        return
    if game.turn == HUMAN_COLOR:
        return
    if not game.get_legal_moves():
        return
    if screen is None:
        ai_move = game.get_ai_move()
    else:
        ai_move = _run_ai_with_modal(game, screen, theme_index)
    if ai_move is not None:
        game.make_move(ai_move)

def _run_ai_with_modal(game, screen, theme_index):
    stop_event = threading.Event()
    result = {"move": None, "error": None}

    def worker():
        try:
            result["move"] = game.get_ai_move(stop_event=stop_event)
        except Exception as exc:  # surface any engine error
            result["error"] = exc

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    show_thinking_modal(screen, game, theme_index, t, stop_event)
    if result["error"] is not None:
        raise result["error"]
    return result["move"]

def _draw_spinner(screen, center, radius, theme, t_ms):
    """CSS-style spinner: ring whose visible arc grows 0->360deg every 2s while
    the whole ring rotates 360deg every 1s."""
    import math
    cx, cy = center
    color = theme["text"]
    thickness = max(3, int(round(radius * 5 / 24)))  # CSS: 5px border on 48px (radius 24)
    rect = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)

    t = t_ms / 1000.0
    rotation = (t % 1.0) * 2 * math.pi          # full revolution per second (CSS clockwise)
    sweep = (t % 2.0) / 2.0 * 2 * math.pi       # 0..2pi over 2s

    if sweep <= 0.001:
        return
    # Convert CSS clockwise-from-top to pygame counterclockwise-from-3-o'clock.
    css_start = rotation
    css_end = rotation + sweep
    py_start = math.pi / 2 - css_end
    py_end = math.pi / 2 - css_start
    pygame.draw.arc(screen, color, rect, py_start, py_end, thickness)

def show_thinking_modal(screen, game, theme_index, thread, stop_event):
    """Block until AI worker finishes. Thorpy modal with a spinner overlay."""
    from thorpy.elements import Button, Text, TitleBox
    _configure_thorpy_for_modal(screen, theme_index)
    theme = get_theme(theme_index)

    def on_force_move():
        stop_event.set()
        tp.loops.quit_current_loop()

    # Wide blank spacer reserves square space the spinner is overdrawn into.
    spinner_spacer = Text("                    \n\n\n")
    label = Text("Searching...")
    force_btn = Button("Force move")
    force_btn.at_unclick = on_force_move

    box = TitleBox("Thinking", children=[spinner_spacer, label, force_btn])
    box.center_on(screen)
    _make_modal_transparent(box)

    _last_size = [screen.get_size()]
    def update_func():
        _draw_background_for_modal(screen, game, theme_index)
        if screen.get_size() != _last_size[0]:
            _last_size[0] = screen.get_size()
            box.center_on(screen)
        if not thread.is_alive():
            tp.loops.quit_current_loop()

    def after_func():
        spacer_rect = spinner_spacer.rect
        radius = max(14, min(spacer_rect.height, spacer_rect.width) // 2 - 4)
        center = (spacer_rect.centerx, spacer_rect.centery)
        _draw_spinner(screen, center, radius, theme, pygame.time.get_ticks())

    box.launch_alone(func_before=update_func, func_after=after_func)
    thread.join()

def attempt_move(game, selected_sq, to_sq, theme_index):
    """Try moving from selected_sq to to_sq. Returns (new_selected_sq, new_cursor_sq)."""
    if selected_sq == to_sq:
        return None, to_sq  # deselect

    board = game.board
    dest_piece = board.grid[to_sq[0]][to_sq[1]]
    # Re-select if clicking another friendly piece
    if dest_piece is not None and dest_piece.color == game.turn:
        return to_sq, to_sq

    # Auto-promote pawn to queen
    piece = board.grid[selected_sq[0]][selected_sq[1]]
    promotion = None
    if piece is not None and piece.kind == "P":
        if (piece.color == 'w' and to_sq[0] == 0) or \
           (piece.color == 'b' and to_sq[0] == board.rows - 1):
            promotion = "Q"

    moved = game.make_move(Move(from_sq=selected_sq, to_sq=to_sq, promotion=promotion))
    if not moved:
        return selected_sq, to_sq  # illegal: keep selection, move cursor
    screen = pygame.display.get_surface()
    apply_ai_move_if_needed(game, screen=screen, theme_index=theme_index)
    return None, to_sq  # clear selection, cursor stays at destination

def handle_mousedown(game, screen, pos, selected_sq, cursor_sq, theme_index):
    """Handle mouse click. Returns (new_selected_sq, new_cursor_sq)."""
    sq = pixel_to_square(screen.get_size(), game.board, pos[0], pos[1],
                        show_coords=_options["show_coords"])
    if sq is None:
        return None, cursor_sq  # click outside board — deselect

    if selected_sq is None:
        if sq in _movable_squares(game):
            return sq, sq  # select only pieces that can actually move
        return None, sq
    else:
        # Only allow moves to legal destination squares
        legal_targets = _legal_targets(game, selected_sq)
        if sq not in legal_targets:
            # Click on invalid square — deselect
            return None, sq
        new_sel, new_cur = attempt_move(game, selected_sq, sq, theme_index)
        return new_sel, new_cur

def handle_keydown(game, key, awaiting_restart, theme_index, selected_sq, cursor_sq, show_help=False, unicode_char=None):
    """Returns (awaiting_restart, show_new_game, theme_index, selected_sq, cursor_sq, show_help)."""
    # Awaiting restart prompt
    if awaiting_restart:
        if key in (pygame.K_y, pygame.K_RETURN):
            game.reset()
            return False, False, theme_index, None, cursor_sq, False
        if key in (pygame.K_n, pygame.K_ESCAPE):
            return False, False, theme_index, None, cursor_sq, False
        return True, False, theme_index, selected_sq, cursor_sq, False

    # History navigation remapped to [ and ]
    if key == pygame.K_LEFTBRACKET:
        game.step_backward()
        return False, False, theme_index, None, cursor_sq, False
    if key == pygame.K_RIGHTBRACKET:
        game.step_forward()
        return False, False, theme_index, None, cursor_sq, False

    # App-level keys
    if key == pygame.K_t:
        return False, False, theme_index + 1, selected_sq, cursor_sq, False
    if key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
        _options["ai_depth"] = min(MAX_AI_DEPTH, _options["ai_depth"] + 1)
        game.ai_depth = _options["ai_depth"]
        game.ai = AI(depth=_options["ai_depth"])
        _set_toast(f"AI strength: L{_options['ai_depth']} ({_strength_label(_options['ai_depth'])})")
        return False, False, theme_index, selected_sq, cursor_sq, False
    if key in (pygame.K_MINUS, pygame.K_KP_MINUS):
        _options["ai_depth"] = max(MIN_AI_DEPTH, _options["ai_depth"] - 1)
        game.ai_depth = _options["ai_depth"]
        game.ai = AI(depth=_options["ai_depth"])
        _set_toast(f"AI strength: L{_options['ai_depth']} ({_strength_label(_options['ai_depth'])})")
        return False, False, theme_index, selected_sq, cursor_sq, False
    if key == pygame.K_p:
        pgn = export_pgn(game)
        if pgn is None:
            print("PGN export only available on 8x8 boards.", file=sys.stderr)
        else:
            print(pgn)
        return False, False, theme_index, selected_sq, cursor_sq, False

    # Keyboard cursor movement (arrow keys + WASD)
    rows, cols = game.board.rows, game.board.cols
    cur = cursor_sq if cursor_sq is not None else _initial_cursor(game)
    dr, dc = 0, 0
    if key in (pygame.K_UP, pygame.K_w):
        dr = -1
    elif key in (pygame.K_DOWN, pygame.K_s):
        dr = 1
    elif key in (pygame.K_LEFT, pygame.K_a):
        dc = -1
    elif key in (pygame.K_RIGHT, pygame.K_d):
        dc = 1

    if dr != 0 or dc != 0:
        if selected_sq is None:
            allowed = _movable_squares(game)
        else:
            allowed = _legal_targets(game, selected_sq)
        new_cursor = _next_in_set(game, cur, dr, dc, allowed)
        return False, False, theme_index, selected_sq, new_cursor, False

    # Space/Enter: select or move
    if key in (pygame.K_SPACE, pygame.K_RETURN):
        if selected_sq is None:
            if cur in _movable_squares(game):
                return False, False, theme_index, cur, cur, False
            return False, False, theme_index, None, cur, False
        else:
            new_sel, new_cur = attempt_move(game, selected_sq, cur, theme_index)
            return False, False, theme_index, new_sel, new_cur, False

    # Escape: deselect
    if key == pygame.K_ESCAPE:
        if selected_sq is not None:
            return False, False, theme_index, None, cursor_sq, False

    return False, False, theme_index, selected_sq, cursor_sq, False

def load_game():
    """Load saved game or create new one with default size."""
    if not SAVE_PATH.exists():
        return Game()
    try:
        return Game.load_from_path(SAVE_PATH)
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        print(f"Warning: could not load saved game from {SAVE_PATH}: {exc}", file=sys.stderr)
        return Game()

def load_or_create_game(screen, theme_index):
    """Resume a saved game in progress, or open the new-game modal."""
    if SAVE_PATH.exists():
        try:
            saved = Game.load_from_path(SAVE_PATH)
            if len(saved.move_history) > 0:
                saved.ai = AI(depth=_options["ai_depth"])
                saved.ai_depth = _options["ai_depth"]
                return saved
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            print(f"Warning: could not load saved game: {exc}", file=sys.stderr)
    return _create_via_modal(screen, theme_index, allow_cancel=True)

def _create_via_modal(screen, theme_index, allow_cancel):
    result = show_new_game_modal(
        screen, theme_index,
        allow_cancel=allow_cancel,
        current_size=DEFAULT_BOARD_SIZE,
        current_depth=_options["ai_depth"],
        piece_surfaces=None,
    )
    if result is None or result == "quit":
        return None
    rows, cols, depth, mode, color, coords = result
    _options["ai_depth"] = depth
    _options["game_mode"] = mode
    _options["player_color"] = color
    _options["show_coords"] = coords
    return create_game_with_size(rows, cols)

def save_game(game):
    game.save_to_path(SAVE_PATH)

def load_options():
    """Load user options from file."""
    if not OPTIONS_PATH.exists():
        return
    try:
        saved_opts = json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))
        # Only load supported keys
        for key in ["show_coords", "ai_depth"]:
            if key in saved_opts:
                _options[key] = saved_opts[key]
    except (OSError, ValueError, KeyError) as exc:
        pass  # Silently ignore errors; use defaults

def save_options():
    """Save user options to file."""
    try:
        OPTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Only save specific keys
        opts_to_save = {k: _options[k] for k in ["show_coords", "ai_depth"]}
        OPTIONS_PATH.write_text(json.dumps(opts_to_save, indent=2), encoding="utf-8")
    except (OSError, TypeError) as exc:
        pass  # Silently ignore errors

def _parse_size(value):
    m = re.fullmatch(r"\s*(\d+)\s*[xX]\s*(\d+)\s*", value)
    if not m:
        raise argparse.ArgumentTypeError(f"size must look like ROWSxCOLS (got {value!r})")
    return (int(m.group(1)), int(m.group(2)))

def _parse_args(argv):
    p = argparse.ArgumentParser(
        prog="micro-mate",
        description="Micro-Mate (Toledo) — tiny chess engine in pygame.",
    )
    p.add_argument("window", nargs="?", type=int, default=720,
                   help="square window size in pixels (default: 720)")
    p.add_argument("--size", type=_parse_size, metavar="RxC",
                   help="board size, e.g. 8x8, 6x6, 4x4, 3x3 (skips menu and saved game)")
    p.add_argument("--new", action="store_true",
                   help="ignore saved game and pick a board size")
    theme_names = [t["name"].lower() for t in THEMES]
    p.add_argument("--theme", choices=theme_names, metavar="NAME",
                   help=f"startup theme: {', '.join(theme_names)}")
    p.add_argument("--no-ai", action="store_true",
                   help="disable the AI (human vs human)")
    p.add_argument("--ai-depth", type=int, default=DEFAULT_AI_DEPTH,
                   choices=range(MIN_AI_DEPTH, MAX_AI_DEPTH + 1),
                   help=f"AI search depth {MIN_AI_DEPTH}-{MAX_AI_DEPTH} (default: {DEFAULT_AI_DEPTH})")
    p.add_argument("--pgn", metavar="FILE",
                   help="load a PGN game (8x8 only; '-' for stdin)")
    p.add_argument("--print-pgn", action="store_true",
                   help="print PGN to stdout on quit (8x8 only)")
    p.add_argument("--coords", action="store_true",
                   help="show file letters and rank numbers around the board")
    return p.parse_args(argv)

def _resolve_initial_theme(args):
    if args.theme is None:
        return DEFAULT_THEME_INDEX
    for i, t in enumerate(THEMES):
        if t["name"].lower() == args.theme:
            return i
    return DEFAULT_THEME_INDEX

def _read_pgn_source(path):
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")

def _initial_game(screen, theme_index, args):
    if args.pgn is not None:
        try:
            text = _read_pgn_source(args.pgn)
        except OSError as exc:
            print(f"Could not read PGN '{args.pgn}': {exc}", file=sys.stderr)
            return None
        game = import_pgn(text, ai_depth=_options["ai_depth"])
        if game is None:
            print("PGN had no game to replay.", file=sys.stderr)
            return None
        return game
    if args.size is not None:
        return create_game_with_size(args.size[0], args.size[1])
    if args.new:
        return _create_via_modal(screen, theme_index, allow_cancel=True)
    return load_or_create_game(screen, theme_index)

def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    load_options()  # Load persisted options first
    _options["ai_enabled"] = not args.no_ai
    _options["ai_depth"] = args.ai_depth
    if args.coords:  # CLI --coords overrides saved setting
        _options["show_coords"] = args.coords

    pygame.init()
    # Wrap set_cursor so unsupported system cursors (e.g. on Raspberry Pi / framebuffer)
    # don't crash the app — thorpy calls this on every button hover.
    _orig_set_cursor = pygame.mouse.set_cursor
    def _safe_set_cursor(cursor):
        try:
            _orig_set_cursor(cursor)
        except pygame.error:
            pass
    pygame.mouse.set_cursor = _safe_set_cursor  # type: ignore[method-assign]

    import thorpy as tp  # noqa: PLC0415 — must be after pygame.init() for Linux cursor support
    globals()['tp'] = tp
    base_window = max(200, args.window)
    size = (base_window, base_window)
    screen = pygame.display.set_mode(size, pygame.RESIZABLE)
    pygame.display.set_caption('Micro-Mate (Toledo)')
    clock = pygame.time.Clock()

    theme_index = _resolve_initial_theme(args)
    # Pre-fit window to default board so the modal preview and post-Start board share the same geometry
    _pre_board = Game(rows=DEFAULT_BOARD_SIZE[0], cols=DEFAULT_BOARD_SIZE[1])
    screen, size = _fit_window_to_board(screen, base_window, _pre_board.board)
    tp.init(screen, tp.theme_classic)  # Initial theme, will be overridden below
    _apply_thorpy_theme(theme_index)
    game = _initial_game(screen, theme_index, args)
    if game is None:
        return 0
    screen, size = _fit_window_to_board(screen, base_window, game.board)
    apply_ai_move_if_needed(game)
    piece_surfaces = load_piece_surfaces()
    awaiting_restart = False
    selected_sq = None
    cursor_sq = None
    show_help = False
    prev_theme_index = theme_index
    _last_click = {"time": 0, "pos": None}
    DOUBLE_CLICK_MS = 300

    def _open_new_game(running):
        nonlocal game, screen, size, selected_sq, cursor_sq
        result = show_new_game_modal(
            screen, theme_index, allow_cancel=True,
            current_size=(game.board.rows, game.board.cols),
            current_depth=_options["ai_depth"],
            piece_surfaces=piece_surfaces,
        )
        if result == "quit":
            return False
        if result is not None:
            rows, cols, depth, mode, color, coords = result
            _options["ai_depth"] = depth
            _options["game_mode"] = mode
            _options["player_color"] = color
            _options["show_coords"] = coords
            game = create_game_with_size(rows, cols)
            selected_sq = None
            cursor_sq = None
            screen, size = _fit_window_to_board(screen, base_window, game.board)
        return running

    running = True
    exit_code = 0
    try:
        while running:
            # Use default thorpy colors (custom theming causes layout issues)
            # if theme_index != prev_theme_index:
            #     _apply_thorpy_theme(theme_index)
            #     prev_theme_index = theme_index

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    unicode_char = getattr(ev, 'unicode', None)
                    if ev.key == pygame.K_ESCAPE and not awaiting_restart and not show_help and selected_sq is None:
                        running = _open_new_game(running)
                        continue
                    if ev.key in (pygame.K_r, pygame.K_n) and not awaiting_restart and not show_help:
                        running = _open_new_game(running)
                        continue
                    if ev.key == pygame.K_c and not awaiting_restart and not show_help:
                        _options["show_coords"] = not _options["show_coords"]
                        screen, size = _fit_window_to_board(screen, base_window, game.board)
                        continue
                    awaiting_restart, should_quit, theme_index, selected_sq, cursor_sq, show_help = handle_keydown(
                        game, ev.key, awaiting_restart, theme_index, selected_sq, cursor_sq, show_help, unicode_char
                    )
                    if should_quit:
                        running = False
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    if ev.button == 1 and not awaiting_restart and not show_help:
                        now = pygame.time.get_ticks()
                        if now - _last_click["time"] <= DOUBLE_CLICK_MS and _last_click["pos"] == ev.pos:
                            running = _open_new_game(running)
                            _last_click["time"] = 0
                        else:
                            _last_click["time"] = now
                            _last_click["pos"] = ev.pos
                            selected_sq, cursor_sq = handle_mousedown(
                                game, screen, ev.pos, selected_sq, cursor_sq, theme_index
                            )
                elif ev.type == pygame.VIDEORESIZE:
                    new_w, new_h = ev.w, ev.h
                    try:
                        desktops = pygame.display.get_desktop_sizes()
                        desk_w, desk_h = desktops[0] if desktops else (new_w, new_h)
                    except (pygame.error, AttributeError):
                        desk_w, desk_h = new_w, new_h
                    # Treat near-desktop sizes as "maximized" and leave them alone.
                    is_maximized = new_w >= int(desk_w * 0.95) or new_h >= int(desk_h * 0.95)
                    if not is_maximized:
                        # Keep window square: use the larger dimension
                        side = max(new_w, new_h)
                        cell = max(40, min(side // game.board.cols, side // game.board.rows))
                        new_w = cell * game.board.cols
                        new_h = cell * game.board.rows
                    if (new_w, new_h) != size:
                        size = (new_w, new_h)
                        screen = pygame.display.set_mode(size, pygame.RESIZABLE)

            screen.fill(get_theme(theme_index)["background"])
            draw_board(
                screen,
                game.board,
                piece_surfaces,
                last_move=game.current_move,
                theme_index=theme_index,
                selected_sq=selected_sq,
                cursor_sq=cursor_sq,
                current_turn=game.turn,
                show_coords=_options["show_coords"],
                king_in_check_sq=game.get_king_check_square(),
            )
            # Phase 7: Help modal via thorpy (called when show_help=True)
            if show_help:
                show_help_modal(screen, game, theme_index, selected_sq)
                show_help = False
            
            # Phase 6: Toast notification (simple pygame text overlay for now)
            if _toast["text"] and pygame.time.get_ticks() < _toast["until"]:
                from micromate.renderer import _get_font
                theme = get_theme(theme_index)
                font = _get_font(20, bold=True)
                if font:
                    label = font.render(_toast["text"], True, theme["text"])
                    pad_x, pad_y = 18, 10
                    rect = pygame.Rect(0, 0, label.get_width() + 2 * pad_x, label.get_height() + 2 * pad_y)
                    rect.midtop = (screen.get_width() // 2, 24)
                    bg = pygame.Surface(rect.size, pygame.SRCALPHA)
                    bg.fill((*theme["panel_fill"], 230))
                    screen.blit(bg, rect.topleft)
                    pygame.draw.rect(screen, theme["panel_border"], rect, 2, border_radius=10)
                    screen.blit(label, label.get_rect(center=rect.center))
            pygame.display.flip()
            clock.tick(60)
    except KeyboardInterrupt:
        # Gracefully exit on Ctrl+C without showing traceback, print board notation
        print_board_notation(game)
        exit_code = 0
    except Exception as exc:
        import traceback
        print(f"Error while running game: {exc}", file=sys.stderr)
        traceback.print_exc()
        exit_code = 1
    finally:
        try:
            save_game(game)
        except OSError as exc:
            print(f"Error: could not save game to {SAVE_PATH}: {exc}", file=sys.stderr)
            exit_code = 1
        save_options()  # Always save options on exit
        if args.print_pgn:
            pgn = export_pgn(game)
            if pgn is None:
                print("PGN export only available on 8x8 boards.", file=sys.stderr)
            else:
                print(pgn)
        pygame.quit()

    return exit_code

if __name__ == '__main__':
    sys.exit(main())
