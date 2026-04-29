# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Run, install, iterate

The project is installed as a tool via `uv`. The entry point `micro-mate` is declared in `pyproject.toml` as `run_game:main`.

- Iterate fast: the tool is installed as an **editable** package (`uv tool install --editable ~/Projects/micro-mate`), so changes to `src/` take effect immediately — just run `micro-mate` without reinstalling. If the editable install ever needs to be refreshed, run that command again.
- Run from a checkout without installing: `uv run python -m src.run_game` from the repo root.
- Useful CLI flags: `--size RxC` (e.g. `8x8`, `5x6`, `4x4`), `--ai-depth 1..5`, `--no-ai`, `--theme NAME`, `--coords`, `--pgn FILE` (`-` for stdin), `--print-pgn`, `--new`. A bare positional integer is the square window size in pixels (default 720).
- Headless smoke tests: `SDL_VIDEODRIVER=dummy /Users/michael/.local/share/uv/tools/micro-mate/bin/python -c "..."` is the established way to exercise renderer / modal code without opening a window. There is no test suite — verify with one-off scripts and direct gameplay.

There is no linter, formatter, or test runner configured. Don't add one without asking.

## Architecture (the bits that span files)

**`src/micromate/engine.py`** — pure-Python chess engine that supports any rectangular board (4×4, 5×6, 6×6, 8×8). Coordinates are `(row, col)` with `(0, 0)` at the top-left (rank 8, file a in standard chess). Key invariants:

- `Board.legal_moves(color)` is the single source of truth for legality. `Game.make_move` rejects any move not in this list. **Move generation is intentionally incomplete: no castling, no en passant.** Pawn promotion auto-queens (`promotion="Q"`).
- `Board._make_move_unsafe` returns the captured piece. Its sibling `_undo_move_unsafe(move, captured)` requires that piece to restore state. The AI search depends on this — earlier versions dropped the captured piece on the floor and silently destroyed material across plies; do not "simplify" undo by removing the `captured` argument.
- `AI` is a fixed-depth minimax with alpha-beta. Eval is material-only from white's POV (positive = white better). `best_move` picks max for white, min for black. Mobility was removed because it doubled per-leaf cost (it called `legal_moves` again) — keep eval cheap or AI feel breaks on 8×8.
- `Game` keeps a list of `GameSnapshot` objects for history (`[`/`]` step). `reset()` rebuilds the AI so `ai_depth` changes during a game persist after restart. JSON save/load (`save_to_path` / `from_state`) round-trips the whole snapshot list.

**`src/micromate/pgn.py`** — PGN import/export for any board size. 8×8 games go through `python-chess` for standard SAN; other sizes use a hand-rolled long-algebraic move list (e.g. `a2-a3`). Every PGN includes a `[BoardSize "RxC"]` header that the importer reads to size the resulting game. Replay stops at the first move our engine can't model (castling, en passant), so `import_pgn` may return a truncated game on 8×8 inputs from external tools.

**`src/micromate/renderer.py`** — pygame draw layer. `board_geometry` and `pixel_to_square` both take `show_coords`; the coordinate border eats real pixels, so click-to-square translation must pass the same flag the renderer used. Themes are a list of dicts at module top — name, square colors, panel colors, and highlight colors. The last-move indicator blends in HSV (saturation boosted, value modulated) so dimming/lightening doesn't desaturate.

**`src/run_game.py`** — single-file UI controller. State is held in locals + a small `_options` dict (`ai_enabled`, `ai_depth`, `show_coords`) and a `_toast` dict for transient messages. Things to know:

- The `pygame.font` circular-import bug on Python 3.14 is why we depend on **`pygame-ce`**, not `pygame`. Don't switch back.
- SVG pieces live in `src/micromate/assets/svg/` so they're packaged via `[tool.setuptools.package-data]`. The renderer searches the package path first, then falls back to a repo-relative path for dev. Adding new assets requires nothing else.
- The window auto-fits the board (`_fit_window_to_board`): cell size derived from the requested base size, window resized to `cols*cell × rows*cell` (+ border for coords). Resize events snap to the same aspect; near-desktop sizes (≥95%) are treated as maximize and left alone.
- Help / new-game / confirm modals run their own blocking event loops. Mouse and keyboard both work — chips and buttons report click rects, and arrows/Tab/Enter mirror them. New-game and `R` (when there are moves) gate on `show_confirm_modal`.

## Project conventions

- Coordinates everywhere are `(row, col)` with row 0 at the top. When working with `python-chess`, convert via `chess.square(col, 7 - row)`.
- `human is white` is hard-coded (`HUMAN_COLOR = 'w'`). The AI plays the other side after each human move via `apply_ai_move_if_needed` — that helper also runs at startup so a saved game on the AI's turn doesn't sit waiting.
- Save file is `~/.micro-mate/save-state.json`. A save with zero moves is treated as "no game" and the new-game modal opens on launch.
- `PLAN.md` tracks engine work and is intended to be deleted once complete (per repo convention, plan files are scratch).

## Web port (`web/`)

A TypeScript / Konva.js / PWA port lives in `web/`. See `web/README.md` for
details. The engine is a direct port of `src/micromate/engine.py` using
`bigint` bitboards (16×16 boards exceed the 53-bit safe integer range).

- Engine semantics are duplicated across Python and TS. **Both must stay in
  sync.** When changing either engine, re-run `uv run python tools/dump_engine_fixtures.py`
  and run `cd web && npm test` — the TS suite asserts parity against the
  Python-dumped fixtures (starting bitboards, perft, AI traces, legal-move
  iteration order).
- AI tie-breaking is sensitive to `legal_moves` iteration order. Don't reorder
  the loops in either engine without re-dumping fixtures.

## Repo-wide rules (from `~/Projects/CLAUDE.md`)

- Commit after each logical batch — don't batch a session of changes into one commit.
- Use `PLAN.md` for multi-step work; check off items as you go.
