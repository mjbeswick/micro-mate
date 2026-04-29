"""PGN import / export for Micro-Mate games of any board size.

Standard 8x8 games are emitted as full SAN PGN via python-chess. Non-8x8
games are emitted with the same `[Event]/[Site]/[Variant "Micro-Mate"]/
[BoardSize "RxC"]/[Result]` headers but a long-algebraic move list
(e.g. `e2-e4`), since python-chess only models 8x8 boards. The
`BoardSize` header lets the importer reconstruct the right-shaped game.
"""
import io
import re
from typing import List, Optional, Tuple

import chess
import chess.pgn

from .engine import Game, Move


_PROMO_TO_CHESS = {"Q": chess.QUEEN, "R": chess.ROOK, "B": chess.BISHOP, "N": chess.KNIGHT}
_PROMO_FROM_CHESS = {chess.QUEEN: "Q", chess.ROOK: "R", chess.BISHOP: "B", chess.KNIGHT: "N"}

_VARIANT_TAG = "Micro-Mate"
_HEADER_RE = re.compile(r'\[(\w+)\s+"([^"]*)"\]')
# Long-algebraic move token: file + rank + '-' + file + rank, optional =Q/R/B/N.
# Multi-digit ranks are accepted so boards with >9 rows still round-trip.
_MOVE_TOKEN_RE = re.compile(r"[a-z]\d+-[a-z]\d+(?:=[QRBN])?", re.IGNORECASE)


def is_pgn_compatible(game: Game) -> bool:
    """Retained for API compatibility — PGN export now supports every size."""
    return True


# --- 8x8 helpers (python-chess bridge) ---

def _to_chess_move(move: Move) -> chess.Move:
    from_sq = chess.square(move.from_sq[1], 7 - move.from_sq[0])
    to_sq = chess.square(move.to_sq[1], 7 - move.to_sq[0])
    promo = _PROMO_TO_CHESS.get(move.promotion.upper()) if move.promotion else None
    return chess.Move(from_sq, to_sq, promotion=promo)


def _from_chess_move(cmove: chess.Move) -> Move:
    from_row = 7 - chess.square_rank(cmove.from_square)
    from_col = chess.square_file(cmove.from_square)
    to_row = 7 - chess.square_rank(cmove.to_square)
    to_col = chess.square_file(cmove.to_square)
    promo = _PROMO_FROM_CHESS.get(cmove.promotion) if cmove.promotion else None
    return Move((from_row, from_col), (to_row, to_col), promotion=promo)


# --- Long-algebraic helpers (any size) ---

def _square_to_alg(row: int, col: int, rows: int) -> str:
    """`(row, col)` → `e4`-style. Rank 1 is the bottom row (row = rows - 1)."""
    return f"{chr(ord('a') + col)}{rows - row}"


def _alg_to_square(text: str, rows: int) -> Tuple[int, int]:
    file_ch = text[0].lower()
    rank = int(text[1:])
    return (rows - rank, ord(file_ch) - ord('a'))


def _move_to_long_alg(move: Move, rows: int) -> str:
    f = _square_to_alg(*move.from_sq, rows=rows)
    t = _square_to_alg(*move.to_sq, rows=rows)
    promo = f"={move.promotion.upper()}" if move.promotion else ""
    return f"{f}-{t}{promo}"


def _long_alg_to_move(token: str, rows: int) -> Move:
    promo = None
    body = token
    if "=" in body:
        body, promo_part = body.split("=", 1)
        promo = promo_part.strip().upper()[:1] or None
    parts = body.split("-")
    if len(parts) != 2:
        raise ValueError(f"Bad move token: {token}")
    return Move(_alg_to_square(parts[0], rows), _alg_to_square(parts[1], rows), promotion=promo)


# --- Header parsing ---

def _read_headers(text: str) -> dict:
    headers = {}
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("["):
            if s == "":
                if headers:
                    break
                continue
            break
        m = _HEADER_RE.match(s)
        if m:
            headers[m.group(1)] = m.group(2)
    return headers


def _parse_board_size(headers: dict) -> Tuple[int, int]:
    spec = headers.get("BoardSize", "8x8")
    try:
        r, c = spec.lower().split("x")
        return int(r), int(c)
    except (ValueError, AttributeError):
        return 8, 8


# --- Public API ---

def export_pgn(game: Game, event: str = "Micro-Mate") -> str:
    """Return PGN text for the move history. 8x8 games use SAN; other sizes
    use long-algebraic move text. Always includes a `[BoardSize]` header."""
    rows, cols = game.board.rows, game.board.cols
    if rows == 8 and cols == 8:
        return _export_pgn_8x8(game, event)
    return _export_pgn_custom(game, event, rows, cols)


def _export_pgn_8x8(game: Game, event: str) -> str:
    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = event
    pgn_game.headers["Site"] = "Micro-Mate"
    # `Variant` is intentionally omitted on 8x8: python-chess validates it
    # against a known-variant registry on render and raises otherwise.
    pgn_game.headers["BoardSize"] = "8x8"
    cb = chess.Board()
    node = pgn_game
    for m in game.move_history:
        cmove = _to_chess_move(m)
        if cmove not in cb.legal_moves:
            break
        node = node.add_variation(cmove)
        cb.push(cmove)
    pgn_game.headers["Result"] = cb.result(claim_draw=False)
    return str(pgn_game)


def _export_pgn_custom(game: Game, event: str, rows: int, cols: int) -> str:
    headers = [
        f'[Event "{event}"]',
        '[Site "Micro-Mate"]',
        f'[Variant "{_VARIANT_TAG}"]',
        f'[BoardSize "{rows}x{cols}"]',
        '[Result "*"]',
    ]
    tokens: List[str] = []
    for i, m in enumerate(game.move_history):
        if i % 2 == 0:
            tokens.append(f"{i // 2 + 1}.")
        tokens.append(_move_to_long_alg(m, rows))
    body = " ".join(tokens + ["*"]) if tokens else "*"
    return "\n".join(headers) + "\n\n" + body + "\n"


def import_pgn(text: str, ai_depth: int = 3) -> Optional[Game]:
    """Replay a PGN's mainline through a fresh game. Sized from the
    `[BoardSize]` header (defaults to 8x8 if absent)."""
    headers = _read_headers(text)
    rows, cols = _parse_board_size(headers)
    if rows == 8 and cols == 8:
        return _import_pgn_8x8(text, ai_depth)
    return _import_pgn_custom(text, rows, cols, ai_depth)


def _import_pgn_8x8(text: str, ai_depth: int) -> Optional[Game]:
    pgn_game = chess.pgn.read_game(io.StringIO(text))
    if pgn_game is None:
        return None
    game = Game(rows=8, cols=8, ai_depth=ai_depth)
    for cmove in pgn_game.mainline_moves():
        if not game.make_move(_from_chess_move(cmove)):
            break
    return game


def _import_pgn_custom(text: str, rows: int, cols: int, ai_depth: int) -> Game:
    # Drop comments and variations, then collect move tokens.
    body = re.sub(r"\{[^}]*\}", " ", text)
    body = re.sub(r"\([^)]*\)", " ", body)
    # Remove header lines so move-shaped strings inside tag values can't leak.
    body = "\n".join(line for line in body.splitlines() if not line.strip().startswith("["))
    game = Game(rows=rows, cols=cols, ai_depth=ai_depth)
    for token in _MOVE_TOKEN_RE.findall(body):
        try:
            mv = _long_alg_to_move(token, rows)
        except ValueError:
            break
        if not game.make_move(mv):
            break
    return game
