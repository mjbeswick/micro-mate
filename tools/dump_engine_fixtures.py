"""Dump engine fixtures as JSON.

Captures starting bitboards per board size, perft counts, and AI move traces.
The TypeScript port consumes this file as ground truth.

Run: uv run python tools/dump_engine_fixtures.py > web/tests/fixtures/engine.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from micromate.engine import AI, Board, Game, Move


BOARD_SIZES = [(3, 3), (4, 4), (6, 6), (8, 8), (10, 10), (16, 16)]


def bb_to_strings(bb):
    return {color: {kind: str(v) for kind, v in bb[color].items()} for color in ("w", "b")}


def perft(board: Board, depth: int, color: str) -> int:
    if depth == 0:
        return 1
    moves = board.legal_moves(color)
    if depth == 1:
        return len(moves)
    total = 0
    next_color = "b" if color == "w" else "w"
    for m in moves:
        cap = board._make_move_unsafe(m)
        total += perft(board, depth - 1, next_color)
        board._undo_move_unsafe(m, cap)
    return total


def dump_starting_positions():
    out = {}
    for rows, cols in BOARD_SIZES:
        b = Board(rows, cols)
        out[f"{rows}x{cols}"] = bb_to_strings(b.bb)
    return out


def dump_perft():
    out = {}
    cases = [
        ("8x8", 8, 8, 2),
        ("4x4", 4, 4, 3),
        ("6x6", 6, 6, 3),
        ("3x3", 3, 3, 3),
    ]
    for name, rows, cols, depth in cases:
        b = Board(rows, cols)
        out[name] = {f"depth{d}": perft(Board(rows, cols), d, "w") for d in range(1, depth + 1)}
    return out


def dump_ai_traces():
    """For each board size, play N plies of AI-vs-AI at depth 2 and record moves."""
    out = {}
    for rows, cols in [(4, 4), (6, 6), (8, 8)]:
        g = Game(rows=rows, cols=cols, ai_depth=2)
        trace = []
        for _ in range(6):
            mv = g.get_ai_move()
            if mv is None:
                break
            trace.append({
                "from": list(mv.from_sq),
                "to": list(mv.to_sq),
                "promotion": mv.promotion,
                "turn_before": g.turn,
            })
            g.make_move(mv)
        out[f"{rows}x{cols}"] = trace
    return out


def dump_legal_move_orders():
    """Capture exact legal-move ordering for startpos so the TS port can lock iteration order."""
    out = {}
    for rows, cols in BOARD_SIZES:
        b = Board(rows, cols)
        moves = b.legal_moves("w")
        out[f"{rows}x{cols}"] = [
            {"from": list(m.from_sq), "to": list(m.to_sq), "promotion": m.promotion}
            for m in moves
        ]
    return out


def main():
    fixtures = {
        "starting_positions": dump_starting_positions(),
        "perft": dump_perft(),
        "ai_traces_depth2": dump_ai_traces(),
        "legal_moves_startpos_white": dump_legal_move_orders(),
    }
    out_path = Path(__file__).resolve().parent.parent / "web" / "tests" / "fixtures" / "engine.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(fixtures, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
