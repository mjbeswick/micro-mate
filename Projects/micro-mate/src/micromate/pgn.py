"""PGN import / export for 8x8 games.

Bridges micromate's (row, col) move format with python-chess. Only
standard 8x8 boards have a meaningful PGN representation, so callers
should check `is_pgn_compatible(game)` first.
"""
import io
from typing import Optional

import chess
import chess.pgn

from .engine import Game, Move


_PROMO_TO_CHESS = {"Q": chess.QUEEN, "R": chess.ROOK, "B": chess.BISHOP, "N": chess.KNIGHT}
_PROMO_FROM_CHESS = {chess.QUEEN: "Q", chess.ROOK: "R", chess.BISHOP: "B", chess.KNIGHT: "N"}


def is_pgn_compatible(game: Game) -> bool:
    return game.board.rows == 8 and game.board.cols == 8


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


def export_pgn(game: Game, event: str = "Micro-Mate") -> Optional[str]:
    """Return the PGN text for the move history, or None if not 8x8."""
    if not is_pgn_compatible(game):
        return None
    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = event
    pgn_game.headers["Site"] = "Micro-Mate"
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


def import_pgn(text: str, ai_depth: int = 3) -> Optional[Game]:
    """Replay a PGN's mainline through a fresh 8x8 game.

    Stops cleanly at the first move micromate's engine cannot replay
    (castling and en passant are not modelled), so the resulting position
    may be a prefix of the source game.
    """
    pgn_game = chess.pgn.read_game(io.StringIO(text))
    if pgn_game is None:
        return None
    game = Game(rows=8, cols=8, ai_depth=ai_depth)
    for cmove in pgn_game.mainline_moves():
        if not game.make_move(_from_chess_move(cmove)):
            break
    return game
