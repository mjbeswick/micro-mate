"""Minimal Toledo Micro-Mate engine — bitboard backend."""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

@dataclass
class Piece:
    kind: str  # 'K','Q','R','B','N','P'
    color: str # 'w' or 'b'

@dataclass
class Move:
    from_sq: Tuple[int,int]
    to_sq: Tuple[int,int]
    promotion: Optional[str] = None

@dataclass
class GameSnapshot:
    bb: dict   # {'w': {kind: int, ...}, 'b': {kind: int, ...}}
    turn: str

_KINDS = ('P', 'N', 'B', 'R', 'Q', 'K')

# Dice mode: each combatant rolls 1d6.
#   attacker > defender → capture succeeds (15 / 36)
#   attacker < defender → attacker is destroyed (15 / 36)
#   attacker = defender → blocked, no change, turn passes (6 / 36)
DICE_P_WIN = 15 / 36
DICE_P_LOSE = 15 / 36
DICE_P_BLOCK = 6 / 36

# King-capture terminal score in pseudo-legal (dice) search. Finite so that
# expectiminimax arithmetic over chance nodes never produces inf - inf = nan.
KING_CAPTURED_VAL = 10_000_000

def _empty_bb():
    return {'w': {k: 0 for k in _KINDS}, 'b': {k: 0 for k in _KINDS}}

def _occ_color(bb, color):
    bbc = bb[color]
    return bbc['P'] | bbc['N'] | bbc['B'] | bbc['R'] | bbc['Q'] | bbc['K']

def _occ_all(bb):
    return _occ_color(bb, 'w') | _occ_color(bb, 'b')


class Board:
    def __init__(self, rows=5, cols=6):
        self.rows = rows
        self.cols = cols
        self.bb = _empty_bb()
        self.setup_startpos()

    # --- Bitboard helpers ---

    def _bit(self, r, c):
        return 1 << (r * self.cols + c)

    def piece_at(self, r, c):
        """Return Piece at (r, c) or None."""
        b = self._bit(r, c)
        for color in ('w', 'b'):
            for kind, bb in self.bb[color].items():
                if bb & b:
                    return Piece(kind, color)
        return None

    def _set_piece(self, r, c, piece):
        self.bb[piece.color][piece.kind] |= self._bit(r, c)

    def evaluate(self, pseudo_legal=False) -> float:
        """Material-only eval: positive = white advantage (centipawns)."""
        king_val = 100_000 if pseudo_legal else 0
        vals = {'P': 100, 'N': 300, 'B': 300, 'R': 500, 'Q': 900, 'K': king_val}
        score = 0.0
        for kind, val in vals.items():
            score += val * bin(self.bb['w'][kind]).count('1')
            score -= val * bin(self.bb['b'][kind]).count('1')
        return score

    @property
    def grid(self):
        """Reconstruct 2D grid from bitboards (used only for serialisation)."""
        result = [[None] * self.cols for _ in range(self.rows)]
        cols = self.cols
        for color in ('w', 'b'):
            for kind, bb in self.bb[color].items():
                tmp = bb
                while tmp:
                    lsb = tmp & (-tmp)
                    sq = lsb.bit_length() - 1
                    r, c = divmod(sq, cols)
                    result[r][c] = Piece(kind, color)
                    tmp ^= lsb
        return result

    # --- Board setup ---

    def setup_startpos(self):
        self.bb = _empty_bb()

        if self.rows < 2:
            return

        if self.rows == 3 and self.cols == 3:
            for c in range(3):
                self._set_piece(0, c, Piece('P', 'b'))
                self._set_piece(2, c, Piece('P', 'w'))
            return

        if self.cols >= 16:
            back_rank = ["R","N","B","Q","K","Q","B","N","R","N","B","Q","Q","B","N","R"]
        elif self.cols >= 10:
            back_rank = ["R","N","B","Q","K","Q","B","N","R","R"]
        elif self.cols >= 8:
            back_rank = ["R","N","B","Q","K","B","N","R"]
        elif self.cols >= 6:
            back_rank = ["R","N","B","Q","K","B"]
        elif self.cols >= 4:
            back_rank = ["R","K","Q","R"]
        else:
            back_rank = ["K","Q"] if self.cols >= 2 else ["K"]

        padded = back_rank[:self.cols] + [None] * max(0, self.cols - len(back_rank))
        reversed_padded = list(reversed(padded))

        for c, kind in enumerate(padded):
            if kind:
                self._set_piece(0, c, Piece(kind, 'b'))
        for c in range(self.cols):
            self._set_piece(1, c, Piece('P', 'b'))
            self._set_piece(self.rows - 2, c, Piece('P', 'w'))
        for c, kind in enumerate(reversed_padded):
            if kind:
                self._set_piece(self.rows - 1, c, Piece(kind, 'w'))

    # --- Move generation ---

    def legal_moves(self, color: str) -> List[Move]:
        moves = []
        for kind in _KINDS:
            tmp = self.bb[color][kind]
            while tmp:
                lsb = tmp & (-tmp)
                sq = lsb.bit_length() - 1
                r, c = divmod(sq, self.cols)
                moves.extend(self._piece_moves(r, c, kind, color))
                tmp ^= lsb
        return [m for m in moves if self._is_legal_move(m, color)]

    def pseudo_legal_moves(self, color: str) -> List[Move]:
        """All moves for color without the 'own king left in check' filter."""
        moves = []
        for kind in _KINDS:
            tmp = self.bb[color][kind]
            while tmp:
                lsb = tmp & (-tmp)
                sq = lsb.bit_length() - 1
                r, c = divmod(sq, self.cols)
                moves.extend(self._piece_moves(r, c, kind, color))
                tmp ^= lsb
        return moves

    def _piece_moves(self, r: int, c: int, kind: str, color: str) -> List[Move]:
        if kind == 'P':
            return self._pawn_moves(r, c, color)
        if kind == 'N':
            return self._knight_moves(r, c, color)
        if kind == 'B':
            return self._sliding_moves(r, c, color, [(-1,-1),(-1,1),(1,-1),(1,1)])
        if kind == 'R':
            return self._sliding_moves(r, c, color, [(-1,0),(1,0),(0,-1),(0,1)])
        if kind == 'Q':
            return self._sliding_moves(r, c, color, [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)])
        if kind == 'K':
            return self._king_moves(r, c, color)
        return []

    def _pawn_moves(self, r: int, c: int, color: str) -> List[Move]:
        moves = []
        direction = -1 if color == 'w' else 1
        new_r = r + direction
        promo_rank = 0 if color == 'w' else self.rows - 1
        cols = self.cols
        occ = _occ_all(self.bb)
        enemy = 'b' if color == 'w' else 'w'
        occ_enemy = _occ_color(self.bb, enemy)

        if 0 <= new_r < self.rows:
            promo = "Q" if new_r == promo_rank else None
            dest_b = 1 << (new_r * cols + c)
            if not (occ & dest_b):
                moves.append(Move((r, c), (new_r, c), promotion=promo))
                if promo is None:
                    if (color == 'w' and r == self.rows - 2) or (color == 'b' and r == 1):
                        two_r = new_r + direction
                        if 0 <= two_r < self.rows and not (occ & (1 << (two_r * cols + c))):
                            moves.append(Move((r, c), (two_r, c)))
            for dc in (-1, 1):
                new_c = c + dc
                if 0 <= new_c < cols:
                    if occ_enemy & (1 << (new_r * cols + new_c)):
                        moves.append(Move((r, c), (new_r, new_c), promotion=promo))
        return moves

    def _knight_moves(self, r: int, c: int, color: str) -> List[Move]:
        moves = []
        occ_own = _occ_color(self.bb, color)
        cols = self.cols
        for dr, dc in ((-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < cols:
                if not (occ_own & (1 << (nr * cols + nc))):
                    moves.append(Move((r, c), (nr, nc)))
        return moves

    def _sliding_moves(self, r: int, c: int, color: str, deltas: List[Tuple[int,int]]) -> List[Move]:
        moves = []
        occ_own = _occ_color(self.bb, color)
        occ = occ_own | _occ_color(self.bb, 'b' if color == 'w' else 'w')
        cols = self.cols
        for dr, dc in deltas:
            nr, nc = r + dr, c + dc
            while 0 <= nr < self.rows and 0 <= nc < cols:
                b = 1 << (nr * cols + nc)
                if occ_own & b:
                    break
                moves.append(Move((r, c), (nr, nc)))
                if occ & b:
                    break
                nr += dr
                nc += dc
        return moves

    def _king_moves(self, r: int, c: int, color: str) -> List[Move]:
        moves = []
        occ_own = _occ_color(self.bb, color)
        cols = self.cols
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < cols:
                    if not (occ_own & (1 << (nr * cols + nc))):
                        moves.append(Move((r, c), (nr, nc)))
        return moves

    # --- Legality / check detection ---

    def _is_legal_move(self, move: Move, color: str) -> bool:
        captured = self._make_move_unsafe(move)
        legal = not self._is_in_check(color)
        self._undo_move_unsafe(move, captured)
        return legal

    def _is_in_check(self, color: str) -> bool:
        king_bb = self.bb[color]['K']
        if not king_bb:
            return False
        sq = king_bb.bit_length() - 1
        king_r, king_c = divmod(sq, self.cols)
        enemy = 'b' if color == 'w' else 'w'
        for kind, bb in self.bb[enemy].items():
            tmp = bb
            while tmp:
                lsb = tmp & (-tmp)
                esq = lsb.bit_length() - 1
                er, ec = divmod(esq, self.cols)
                if self._can_piece_attack(er, ec, king_r, king_c, kind, enemy):
                    return True
                tmp ^= lsb
        return False

    def _ray_attacks(self, r: int, c: int, dr: int, dc: int, target_r: int, target_c: int) -> bool:
        occ = _occ_all(self.bb)
        cols = self.cols
        nr, nc = r + dr, c + dc
        while 0 <= nr < self.rows and 0 <= nc < cols:
            if nr == target_r and nc == target_c:
                return True
            if occ & (1 << (nr * cols + nc)):
                return False
            nr += dr
            nc += dc
        return False

    def _can_piece_attack(self, r: int, c: int, target_r: int, target_c: int,
                          kind: Optional[str] = None, color: Optional[str] = None) -> bool:
        if kind is None or color is None:
            p = self.piece_at(r, c)
            if not p:
                return False
            kind, color = p.kind, p.color
        dr = target_r - r
        dc = target_c - c

        if kind == 'P':
            direction = -1 if color == 'w' else 1
            return dr == direction and abs(dc) == 1
        if kind == 'N':
            return (abs(dr), abs(dc)) in {(2, 1), (1, 2)}
        if kind == 'K':
            return max(abs(dr), abs(dc)) == 1
        if kind in ('B', 'Q') and dr != 0 and abs(dr) == abs(dc):
            if self._ray_attacks(r, c, 1 if dr > 0 else -1, 1 if dc > 0 else -1, target_r, target_c):
                return True
        if kind in ('R', 'Q') and (dr == 0 or dc == 0):
            step_r = (1 if dr > 0 else -1) if dr != 0 else 0
            step_c = (1 if dc > 0 else -1) if dc != 0 else 0
            if self._ray_attacks(r, c, step_r, step_c, target_r, target_c):
                return True
        return False

    # --- Make / undo (for AI search and legality checking) ---

    def _make_move_unsafe(self, move: Move) -> Optional[Piece]:
        """Execute move without legality check. Returns captured piece."""
        r_f, c_f = move.from_sq
        r_t, c_t = move.to_sq
        cols = self.cols
        fb = 1 << (r_f * cols + c_f)
        tb = 1 << (r_t * cols + c_t)
        bb_w = self.bb['w']
        bb_b = self.bb['b']

        # Determine moving piece color and kind
        occ_w = bb_w['P'] | bb_w['N'] | bb_w['B'] | bb_w['R'] | bb_w['Q'] | bb_w['K']
        moving_bb = bb_w if (occ_w & fb) else bb_b
        moving_kind = next(k for k, bb in moving_bb.items() if bb & fb)

        # Find and remove captured piece
        captured = None
        occ_all = occ_w | (bb_b['P'] | bb_b['N'] | bb_b['B'] | bb_b['R'] | bb_b['Q'] | bb_b['K'])
        if occ_all & tb:
            cap_bb = bb_w if (occ_w & tb) else bb_b
            cap_color = 'w' if cap_bb is bb_w else 'b'
            cap_kind = next(k for k, bb in cap_bb.items() if bb & tb)
            captured = Piece(cap_kind, cap_color)
            cap_bb[cap_kind] ^= tb

        # Move piece (handle promotion)
        moving_bb[moving_kind] ^= fb
        place_kind = move.promotion if (moving_kind == 'P' and move.promotion) else moving_kind
        moving_bb[place_kind] |= tb

        return captured

    def _undo_move_unsafe(self, move: Move, captured: Optional[Piece]) -> None:
        """Undo a move made with _make_move_unsafe."""
        r_f, c_f = move.from_sq
        r_t, c_t = move.to_sq
        cols = self.cols
        fb = 1 << (r_f * cols + c_f)
        tb = 1 << (r_t * cols + c_t)
        bb_w = self.bb['w']
        bb_b = self.bb['b']

        # Find piece at destination
        occ_w = bb_w['P'] | bb_w['N'] | bb_w['B'] | bb_w['R'] | bb_w['Q'] | bb_w['K']
        dest_bb = bb_w if (occ_w & tb) else bb_b
        dest_kind = next(k for k, bb in dest_bb.items() if bb & tb)

        # Remove from destination; restore original kind at source
        dest_bb[dest_kind] ^= tb
        restore_kind = 'P' if move.promotion else dest_kind
        dest_bb[restore_kind] |= fb

        # Restore captured piece
        if captured:
            self.bb[captured.color][captured.kind] |= tb

    def _make_attacker_loss_unsafe(self, move: Move) -> Piece:
        """Dice combat: attacker loses — clear the piece on its origin square.
        Defender untouched. Returns the removed piece so undo can restore it."""
        r_f, c_f = move.from_sq
        fb = 1 << (r_f * self.cols + c_f)
        bb_w = self.bb['w']
        occ_w = bb_w['P'] | bb_w['N'] | bb_w['B'] | bb_w['R'] | bb_w['Q'] | bb_w['K']
        if occ_w & fb:
            piece_bb, color = bb_w, 'w'
        else:
            piece_bb, color = self.bb['b'], 'b'
        kind = next(k for k, bb in piece_bb.items() if bb & fb)
        piece_bb[kind] ^= fb
        return Piece(kind, color)

    def _undo_attacker_loss_unsafe(self, move: Move, piece: Piece) -> None:
        r_f, c_f = move.from_sq
        fb = 1 << (r_f * self.cols + c_f)
        self.bb[piece.color][piece.kind] |= fb


class AI:
    """Minimax with alpha-beta pruning. Eval is from white's POV."""

    def __init__(self, depth=3):
        self.depth = depth

    def best_move(self, board: "Board", color: str, stop_event=None,
                  pseudo_legal: bool = False) -> Optional[Move]:
        moves = board.pseudo_legal_moves(color) if pseudo_legal else board.legal_moves(color)
        if not moves:
            return None
        moves.sort(key=lambda m: board.piece_at(m.to_sq[0], m.to_sq[1]) is not None, reverse=True)
        best = moves[0]
        is_max = (color == 'w')
        best_score = float('-inf') if is_max else float('inf')
        for move in moves:
            if stop_event is not None and stop_event.is_set():
                break
            score = self._score_move(board, move, self.depth - 1, float('-inf'), float('inf'),
                                     not is_max, stop_event, pseudo_legal)
            if is_max:
                if score > best_score:
                    best_score, best = score, move
            else:
                if score < best_score:
                    best_score, best = score, move
        return best

    def _score_move(self, board: "Board", move: Move, depth: int, alpha: float, beta: float,
                    next_is_maximizing: bool, stop_event, pseudo_legal: bool) -> float:
        """Score `move` from the parent node's POV. In dice mode, captures
        expand into a chance node over the three combat outcomes."""
        is_capture = board.piece_at(move.to_sq[0], move.to_sq[1]) is not None
        if pseudo_legal and is_capture:
            return self._capture_chance_value(board, move, depth, next_is_maximizing, stop_event)
        captured = board._make_move_unsafe(move)
        score = self._minimax(board, depth, alpha, beta, next_is_maximizing, stop_event, pseudo_legal)
        board._undo_move_unsafe(move, captured)
        return score

    def _capture_chance_value(self, board: "Board", move: Move, depth: int,
                              next_is_maximizing: bool, stop_event) -> float:
        """Expectiminimax over the three dice outcomes of a capture.
        Children use a full alpha/beta window — pruning across chance siblings
        would require star-pruning, not worth the complexity for 3 outcomes."""
        NEG, POS = float('-inf'), float('inf')

        # 1. Attacker wins — capture succeeds.
        captured = board._make_move_unsafe(move)
        s_win = self._minimax(board, depth, NEG, POS, next_is_maximizing, stop_event, True)
        board._undo_move_unsafe(move, captured)

        # 2. Attacker loses — attacker piece destroyed on its origin.
        lost = board._make_attacker_loss_unsafe(move)
        s_lose = self._minimax(board, depth, NEG, POS, next_is_maximizing, stop_event, True)
        board._undo_attacker_loss_unsafe(move, lost)

        # 3. Blocked — board unchanged, turn still passes.
        s_block = self._minimax(board, depth, NEG, POS, next_is_maximizing, stop_event, True)

        return DICE_P_WIN * s_win + DICE_P_LOSE * s_lose + DICE_P_BLOCK * s_block

    def _minimax(self, board: "Board", depth: int, alpha: float, beta: float,
                 is_maximizing: bool, stop_event=None, pseudo_legal: bool = False) -> float:
        if pseudo_legal:
            # King captured = terminal win/loss regardless of depth.
            # Use a finite large value so chance-node arithmetic stays well-defined.
            if not board.bb['b']['K']:
                return KING_CAPTURED_VAL
            if not board.bb['w']['K']:
                return -KING_CAPTURED_VAL
        if depth == 0:
            return self._evaluate(board, pseudo_legal)
        if stop_event is not None and stop_event.is_set():
            return self._evaluate(board, pseudo_legal)
        color = 'w' if is_maximizing else 'b'
        moves = board.pseudo_legal_moves(color) if pseudo_legal else board.legal_moves(color)
        moves.sort(key=lambda m: board.piece_at(m.to_sq[0], m.to_sq[1]) is not None, reverse=True)
        if not moves:
            if pseudo_legal:
                return 0  # no moves = stalemate
            return (float('-inf') if is_maximizing else float('inf')) if board._is_in_check(color) else 0
        if is_maximizing:
            max_score = float('-inf')
            for move in moves:
                if stop_event is not None and stop_event.is_set():
                    break
                score = self._score_move(board, move, depth - 1, alpha, beta, False, stop_event, pseudo_legal)
                if score > max_score:
                    max_score = score
                alpha = max(alpha, score)
                if beta <= alpha:
                    break
            return max_score
        else:
            min_score = float('inf')
            for move in moves:
                if stop_event is not None and stop_event.is_set():
                    break
                score = self._score_move(board, move, depth - 1, alpha, beta, True, stop_event, pseudo_legal)
                if score < min_score:
                    min_score = score
                beta = min(beta, score)
                if beta <= alpha:
                    break
            return min_score

    def _evaluate(self, board: "Board", pseudo_legal: bool = False) -> float:
        """Material-only eval via popcount — positive = white advantage."""
        # In king-capture mode give the king an extreme value so the AI treats
        # capturing / losing it as the dominant objective.
        king_val = 100_000 if pseudo_legal else 0
        vals = {'P': 100, 'N': 300, 'B': 300, 'R': 500, 'Q': 900, 'K': king_val}
        score = 0
        for kind, val in vals.items():
            score += val * bin(board.bb['w'][kind]).count('1')
            score -= val * bin(board.bb['b'][kind]).count('1')
        return score


class Game:
    def __init__(self, rows=5, cols=6, ai_depth=3):
        self.board = Board(rows, cols)
        self.turn = 'w'
        self.move_history: List[Move] = []
        self._history: List[GameSnapshot] = [self._snapshot()]
        self._history_index = 0
        self.ai_depth = ai_depth
        self.ai = AI(depth=ai_depth)
        self._king_check_sq: Optional[tuple] = None
        self._king_check_valid = False

    def _clone_bb(self):
        return {'w': dict(self.board.bb['w']), 'b': dict(self.board.bb['b'])}

    def _snapshot(self) -> GameSnapshot:
        return GameSnapshot(bb=self._clone_bb(), turn=self.turn)

    def _restore_snapshot(self, snapshot: GameSnapshot):
        self.board.bb = {'w': dict(snapshot.bb['w']), 'b': dict(snapshot.bb['b'])}
        self.turn = snapshot.turn
        self._king_check_valid = False

    def record_position(self):
        if self._history_index < len(self._history) - 1:
            self._history = self._history[:self._history_index + 1]
        self._history.append(self._snapshot())
        self._history_index = len(self._history) - 1

    @property
    def position_index(self) -> int:
        return self._history_index

    @property
    def position_count(self) -> int:
        return len(self._history)

    @property
    def current_move(self) -> Optional[Move]:
        if self._history_index == 0:
            return None
        move_index = self._history_index - 1
        if move_index >= len(self.move_history):
            return None
        return self.move_history[move_index]

    def can_step_backward(self) -> bool:
        return self._history_index > 0

    def can_step_forward(self) -> bool:
        return self._history_index < len(self._history) - 1

    def step_backward(self) -> bool:
        if not self.can_step_backward():
            return False
        self._history_index -= 1
        self._restore_snapshot(self._history[self._history_index])
        return True

    def step_forward(self) -> bool:
        if not self.can_step_forward():
            return False
        self._history_index += 1
        self._restore_snapshot(self._history[self._history_index])
        return True

    def reset(self):
        self.board = Board(self.board.rows, self.board.cols)
        self.turn = 'w'
        self.move_history.clear()
        self._history = [self._snapshot()]
        self._history_index = 0
        self.ai = AI(depth=self.ai_depth)
        self._king_check_valid = False

    def get_legal_moves(self, pseudo_legal: bool = False) -> List[Move]:
        if pseudo_legal:
            return self.board.pseudo_legal_moves(self.turn)
        return self.board.legal_moves(self.turn)

    def get_king_check_square(self) -> Optional[tuple]:
        if not self._king_check_valid:
            self._king_check_sq = None
            if self.board._is_in_check(self.turn):
                king_bb = self.board.bb[self.turn]['K']
                if king_bb:
                    sq = king_bb.bit_length() - 1
                    self._king_check_sq = divmod(sq, self.board.cols)
            self._king_check_valid = True
        return self._king_check_sq

    def get_ai_move(self, stop_event=None, pseudo_legal: bool = False) -> Optional[Move]:
        """Return AI's best move searched on a scratch copy of the board."""
        scratch = Board(self.board.rows, self.board.cols)
        scratch.bb = self._clone_bb()
        return self.ai.best_move(scratch, self.turn, stop_event=stop_event,
                                 pseudo_legal=pseudo_legal)

    def make_move(self, move: Move, pseudo_legal: bool = False) -> bool:
        moves = self.board.pseudo_legal_moves(self.turn) if pseudo_legal else self.board.legal_moves(self.turn)
        if not any(m.from_sq == move.from_sq and m.to_sq == move.to_sq for m in moves):
            return False
        if self._history_index < len(self._history) - 1:
            self.move_history = self.move_history[:self._history_index]
        self.move_history.append(move)
        self.board._make_move_unsafe(move)
        self.turn = 'b' if self.turn == 'w' else 'w'
        self._king_check_valid = False
        self.record_position()
        return True

    def make_attacker_loss(self, move: Move) -> None:
        """Combat result: attacker's piece is destroyed on its own square; defender stays.
        Advances the turn and records a history snapshot."""
        r_f, c_f = move.from_sq
        piece = self.board.piece_at(r_f, c_f)
        if piece:
            self.board.bb[piece.color][piece.kind] &= ~self.board._bit(r_f, c_f)
        if self._history_index < len(self._history) - 1:
            self.move_history = self.move_history[:self._history_index]
        self.move_history.append(move)
        self.turn = 'b' if self.turn == 'w' else 'w'
        self._king_check_valid = False
        self.record_position()

    def skip_turn(self, move: Move) -> None:
        """Combat result: attack blocked, no pieces change. Advances the turn."""
        if self._history_index < len(self._history) - 1:
            self.move_history = self.move_history[:self._history_index]
        self.move_history.append(move)
        self.turn = 'b' if self.turn == 'w' else 'w'
        self._king_check_valid = False
        self.record_position()

    # --- Serialisation helpers ---

    @staticmethod
    def _serialize_piece(piece: Optional[Piece]):
        if piece is None:
            return None
        return {"kind": piece.kind, "color": piece.color}

    @staticmethod
    def _deserialize_piece(piece_data):
        if piece_data is None:
            return None
        return Piece(piece_data["kind"], piece_data["color"])

    @staticmethod
    def _serialize_move(move: Move):
        return {
            "from_sq": [move.from_sq[0], move.from_sq[1]],
            "to_sq": [move.to_sq[0], move.to_sq[1]],
            "promotion": move.promotion,
        }

    @staticmethod
    def _deserialize_move(move_data):
        return Move(
            from_sq=(move_data["from_sq"][0], move_data["from_sq"][1]),
            to_sq=(move_data["to_sq"][0], move_data["to_sq"][1]),
            promotion=move_data.get("promotion"),
        )

    @staticmethod
    def _bb_from_grid(grid, rows, cols):
        bb = _empty_bb()
        for r in range(rows):
            for c in range(cols):
                p = grid[r][c]
                if p is not None:
                    bb[p.color][p.kind] |= 1 << (r * cols + c)
        return bb

    def to_state(self):
        rows, cols = self.board.rows, self.board.cols
        return {
            "rows": rows,
            "cols": cols,
            "turn": self.turn,
            "position_index": self._history_index,
            "move_history": [self._serialize_move(m) for m in self.move_history],
            "history": [
                {
                    "turn": snap.turn,
                    "grid": [
                        [
                            self._serialize_piece(
                                next(
                                    (Piece(k, color)
                                     for color in ('w', 'b')
                                     for k, bb in snap.bb[color].items()
                                     if bb & (1 << (r * cols + c))),
                                    None
                                )
                            )
                            for c in range(cols)
                        ]
                        for r in range(rows)
                    ],
                }
                for snap in self._history
            ],
        }

    @classmethod
    def from_state(cls, state):
        rows = state["rows"]
        cols = state["cols"]
        game = cls(rows=rows, cols=cols)
        game.turn = state["turn"]
        game.move_history = [cls._deserialize_move(m) for m in state["move_history"]]
        game._history = []
        for snap_data in state["history"]:
            grid = [
                [cls._deserialize_piece(p) for p in row]
                for row in snap_data["grid"]
            ]
            bb = cls._bb_from_grid(grid, rows, cols)
            game._history.append(GameSnapshot(bb=bb, turn=snap_data["turn"]))
        game._history_index = state["position_index"]
        game._restore_snapshot(game._history[game._history_index])
        return game

    def save_to_path(self, path):
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(json.dumps(self.to_state(), indent=2), encoding="utf-8")

    @classmethod
    def load_from_path(cls, path):
        save_path = Path(path)
        state = json.loads(save_path.read_text(encoding="utf-8"))
        return cls.from_state(state)
