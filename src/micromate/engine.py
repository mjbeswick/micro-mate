"""Minimal Toledo Micro-Mate engine skeleton."""
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
    grid: List[List[Optional["Piece"]]]
    turn: str

class Board:
    def __init__(self, rows=5, cols=6):
        self.rows = rows
        self.cols = cols
        self.grid = [[None for _ in range(cols)] for _ in range(rows)]
        self.setup_startpos()

    def setup_startpos(self):
        self.grid = [[None for _ in range(self.cols)] for _ in range(self.rows)]

        if self.rows < 2:
            return

        # Special case: 3x3 board with just pawns
        if self.rows == 3 and self.cols == 3:
            self.grid[0] = [Piece("P", "b"), Piece("P", "b"), Piece("P", "b")]
            self.grid[2] = [Piece("P", "w"), Piece("P", "w"), Piece("P", "w")]
            return

        # Build back rank based on board width
        if self.cols >= 16:
            back_rank = ["R", "N", "B", "Q", "K", "Q", "B", "N", "R", "N", "B", "Q", "Q", "B", "N", "R"]
        elif self.cols >= 10:
            back_rank = ["R", "N", "B", "Q", "K", "Q", "B", "N", "R", "R"]
        elif self.cols >= 8:
            back_rank = ["R", "N", "B", "Q", "K", "B", "N", "R"]
        elif self.cols >= 6:
            back_rank = ["R", "N", "B", "Q", "K", "B"]
        elif self.cols >= 4:
            back_rank = ["R", "K", "Q", "R"]
        else:
            back_rank = ["K", "Q"] if self.cols >= 2 else ["K"]

        pawn_rank = ["P"] * self.cols

        # Pad back_rank to match column count and place pieces
        back_rank_padded = back_rank[:self.cols] + [None] * (self.cols - len(back_rank[:self.cols]))
        self.grid[0] = [Piece(kind, "b") if kind else None for kind in back_rank_padded]
        self.grid[1] = [Piece(kind, "b") for kind in pawn_rank]
        self.grid[-2] = [Piece(kind, "w") for kind in pawn_rank]
        back_rank_reversed = list(reversed(back_rank_padded))
        self.grid[-1] = [Piece(kind, "w") if kind else None for kind in back_rank_reversed]

    def legal_moves(self, color: str) -> List[Move]:
        """Generate all legal moves for a color."""
        moves = []
        for r in range(self.rows):
            for c in range(self.cols):
                piece = self.grid[r][c]
                if piece and piece.color == color:
                    moves.extend(self._piece_moves(r, c))
        return [m for m in moves if self._is_legal_move(m, color)]

    def _piece_moves(self, r: int, c: int) -> List[Move]:
        """Generate all pseudo-legal moves for piece at (r, c)."""
        piece = self.grid[r][c]
        if not piece:
            return []

        if piece.kind == "P":
            return self._pawn_moves(r, c, piece.color)
        elif piece.kind == "N":
            return self._knight_moves(r, c)
        elif piece.kind == "B":
            return self._bishop_moves(r, c)
        elif piece.kind == "R":
            return self._rook_moves(r, c)
        elif piece.kind == "Q":
            return self._queen_moves(r, c)
        elif piece.kind == "K":
            return self._king_moves(r, c)
        return []

    def _pawn_moves(self, r: int, c: int, color: str) -> List[Move]:
        moves = []
        direction = -1 if color == 'w' else 1
        new_r = r + direction
        promo_rank = 0 if color == 'w' else self.rows - 1

        if 0 <= new_r < self.rows:
            promo = "Q" if new_r == promo_rank else None
            if self.grid[new_r][c] is None:
                moves.append(Move((r, c), (new_r, c), promotion=promo))
                # Two-square advance from starting position (never a promotion rank)
                if promo is None:
                    if (color == 'w' and r == self.rows - 2) or (color == 'b' and r == 1):
                        two_sq_r = new_r + direction
                        if 0 <= two_sq_r < self.rows and self.grid[two_sq_r][c] is None:
                            moves.append(Move((r, c), (two_sq_r, c)))
            # Captures
            for dc in [-1, 1]:
                new_c = c + dc
                if 0 <= new_c < self.cols:
                    target = self.grid[new_r][new_c]
                    if target and target.color != color:
                        moves.append(Move((r, c), (new_r, new_c), promotion=promo))
        return moves

    def _knight_moves(self, r: int, c: int) -> List[Move]:
        moves = []
        deltas = [(-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)]
        piece_color = self.grid[r][c].color
        for dr, dc in deltas:
            new_r, new_c = r + dr, c + dc
            if 0 <= new_r < self.rows and 0 <= new_c < self.cols:
                target = self.grid[new_r][new_c]
                if target is None or target.color != piece_color:
                    moves.append(Move((r, c), (new_r, new_c)))
        return moves

    def _sliding_moves(self, r: int, c: int, deltas: List[Tuple[int, int]]) -> List[Move]:
        moves = []
        piece_color = self.grid[r][c].color
        for dr, dc in deltas:
            nr, nc = r + dr, c + dc
            while 0 <= nr < self.rows and 0 <= nc < self.cols:
                target = self.grid[nr][nc]
                if target is None:
                    moves.append(Move((r, c), (nr, nc)))
                elif target.color != piece_color:
                    moves.append(Move((r, c), (nr, nc)))
                    break
                else:
                    break
                nr += dr
                nc += dc
        return moves

    def _bishop_moves(self, r: int, c: int) -> List[Move]:
        return self._sliding_moves(r, c, [(-1,-1), (-1,1), (1,-1), (1,1)])

    def _rook_moves(self, r: int, c: int) -> List[Move]:
        return self._sliding_moves(r, c, [(-1,0), (1,0), (0,-1), (0,1)])

    def _queen_moves(self, r: int, c: int) -> List[Move]:
        return self._sliding_moves(r, c, [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)])

    def _king_moves(self, r: int, c: int) -> List[Move]:
        moves = []
        piece_color = self.grid[r][c].color
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                new_r, new_c = r + dr, c + dc
                if 0 <= new_r < self.rows and 0 <= new_c < self.cols:
                    target = self.grid[new_r][new_c]
                    if target is None or target.color != piece_color:
                        moves.append(Move((r, c), (new_r, new_c)))
        return moves

    def _is_legal_move(self, move: Move, color: str) -> bool:
        """Check if move is legal (doesn't leave king in check)."""
        r_from, c_from = move.from_sq
        r_to, c_to = move.to_sq

        # Make move
        piece = self.grid[r_from][c_from]
        captured = self.grid[r_to][c_to]
        self.grid[r_to][c_to] = piece
        self.grid[r_from][c_from] = None

        # Check if king is in check
        legal = not self._is_in_check(color)

        # Undo move
        self.grid[r_from][c_from] = piece
        self.grid[r_to][c_to] = captured

        return legal

    def _is_in_check(self, color: str) -> bool:
        """Check if color's king is under attack."""
        king_pos = None
        for r in range(self.rows):
            for c in range(self.cols):
                piece = self.grid[r][c]
                if piece and piece.kind == "K" and piece.color == color:
                    king_pos = (r, c)
                    break

        if not king_pos:
            return False

        # Check if any opponent piece can attack king
        enemy_color = 'b' if color == 'w' else 'w'
        for r in range(self.rows):
            for c in range(self.cols):
                piece = self.grid[r][c]
                if piece and piece.color == enemy_color:
                    if self._can_piece_attack(r, c, king_pos[0], king_pos[1]):
                        return True
        return False

    def _ray_attacks(self, r: int, c: int, dr: int, dc: int, target_r: int, target_c: int) -> bool:
        """Walk ray from (r,c) in direction (dr,dc); return True if target reached unobstructed."""
        nr, nc = r + dr, c + dc
        while 0 <= nr < self.rows and 0 <= nc < self.cols:
            if nr == target_r and nc == target_c:
                return True
            if self.grid[nr][nc] is not None:
                return False
            nr += dr
            nc += dc
        return False

    def _can_piece_attack(self, r: int, c: int, target_r: int, target_c: int) -> bool:
        """Check if piece at (r,c) can attack (target_r, target_c)."""
        piece = self.grid[r][c]
        if not piece:
            return False
        dr = target_r - r
        dc = target_c - c
        kind = piece.kind

        if kind == 'P':
            direction = -1 if piece.color == 'w' else 1
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

    def _make_move_unsafe(self, move: Move) -> Optional[Piece]:
        """Make move without validation (for AI search). Returns captured piece."""
        r_from, c_from = move.from_sq
        r_to, c_to = move.to_sq
        piece = self.grid[r_from][c_from]
        captured = self.grid[r_to][c_to]
        self.grid[r_to][c_to] = piece
        self.grid[r_from][c_from] = None
        if piece and piece.kind == "P" and move.promotion:
            self.grid[r_to][c_to] = Piece(move.promotion, piece.color)
        return captured

    def _undo_move_unsafe(self, move: Move, captured: Optional[Piece]) -> None:
        """Undo move made with _make_move_unsafe, restoring any captured piece."""
        r_from, c_from = move.from_sq
        r_to, c_to = move.to_sq
        piece = self.grid[r_to][c_to]
        if piece and move.promotion:
            piece = Piece("P", piece.color)
        self.grid[r_from][c_from] = piece
        self.grid[r_to][c_to] = captured

class AI:
    """Chess AI using minimax with alpha-beta pruning. Eval is from white's POV."""

    def __init__(self, depth=3):
        self.depth = depth

    def best_move(self, board: "Board", color: str, stop_event=None) -> Optional[Move]:
        """Return the best move for `color`. If stop_event is set mid-search,
        return the best move found so far (or the first legal move)."""
        moves = board.legal_moves(color)
        if not moves:
            return None
        moves.sort(key=lambda m: board.grid[m.to_sq[0]][m.to_sq[1]] is not None, reverse=True)
        best = moves[0]  # fallback so cancellation always yields something legal
        if color == 'w':
            best_score = float('-inf')
            for move in moves:
                if stop_event is not None and stop_event.is_set():
                    break
                captured = board._make_move_unsafe(move)
                score = self._minimax(board, self.depth - 1, float('-inf'), float('inf'), False, stop_event)
                board._undo_move_unsafe(move, captured)
                if score > best_score:
                    best_score, best = score, move
        else:
            best_score = float('inf')
            for move in moves:
                if stop_event is not None and stop_event.is_set():
                    break
                captured = board._make_move_unsafe(move)
                score = self._minimax(board, self.depth - 1, float('-inf'), float('inf'), True, stop_event)
                board._undo_move_unsafe(move, captured)
                if score < best_score:
                    best_score, best = score, move
        return best

    def _minimax(self, board: "Board", depth: int, alpha: float, beta: float, is_maximizing: bool, stop_event=None) -> float:
        if depth == 0:
            return self._evaluate(board)
        if stop_event is not None and stop_event.is_set():
            return self._evaluate(board)
        color = 'w' if is_maximizing else 'b'
        moves = board.legal_moves(color)
        moves.sort(key=lambda m: board.grid[m.to_sq[0]][m.to_sq[1]] is not None, reverse=True)
        if not moves:
            if board._is_in_check(color):
                return float('-inf') if is_maximizing else float('inf')
            return 0
        if is_maximizing:
            max_score = float('-inf')
            for move in moves:
                if stop_event is not None and stop_event.is_set():
                    break
                captured = board._make_move_unsafe(move)
                score = self._minimax(board, depth - 1, alpha, beta, False, stop_event)
                board._undo_move_unsafe(move, captured)
                if score > max_score:
                    max_score = score
                if score > alpha:
                    alpha = score
                if beta <= alpha:
                    break
            return max_score
        else:
            min_score = float('inf')
            for move in moves:
                if stop_event is not None and stop_event.is_set():
                    break
                captured = board._make_move_unsafe(move)
                score = self._minimax(board, depth - 1, alpha, beta, True, stop_event)
                board._undo_move_unsafe(move, captured)
                if score < min_score:
                    min_score = score
                if score < beta:
                    beta = score
                if beta <= alpha:
                    break
            return min_score

    def _evaluate(self, board: "Board") -> float:
        """Material-only eval — positive = white advantage."""
        material = 0
        piece_values = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 0}
        for row in board.grid:
            for piece in row:
                if piece is None:
                    continue
                v = piece_values.get(piece.kind, 0)
                material += v if piece.color == 'w' else -v
        return material * 100


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

    def _clone_grid(self) -> List[List[Optional[Piece]]]:
        return [
            [None if piece is None else Piece(piece.kind, piece.color) for piece in row]
            for row in self.board.grid
        ]

    def _snapshot(self) -> GameSnapshot:
        return GameSnapshot(grid=self._clone_grid(), turn=self.turn)

    def _restore_snapshot(self, snapshot: GameSnapshot):
        self.board.grid = [
            [None if piece is None else Piece(piece.kind, piece.color) for piece in row]
            for row in snapshot.grid
        ]
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

    def get_legal_moves(self) -> List[Move]:
        """Get legal moves for current player."""
        return self.board.legal_moves(self.turn)

    def get_king_check_square(self) -> Optional[tuple]:
        """Return the king's position if it's in check, None otherwise."""
        if not self._king_check_valid:
            self._king_check_sq = None
            if self.board._is_in_check(self.turn):
                for r in range(self.board.rows):
                    for c in range(self.board.cols):
                        piece = self.board.grid[r][c]
                        if piece and piece.kind == "K" and piece.color == self.turn:
                            self._king_check_sq = (r, c)
                            break
            self._king_check_valid = True
        return self._king_check_sq

    def get_ai_move(self, stop_event=None) -> Optional[Move]:
        """Get AI's best move for current player. Cancellable via stop_event.
        Searches on a copy of the board so the live board isn't mutated
        mid-search (which would cause visual glitches during rendering)."""
        scratch = Board(self.board.rows, self.board.cols)
        scratch.grid = self._clone_grid()
        return self.ai.best_move(scratch, self.turn, stop_event=stop_event)

    def make_move(self, move: Move) -> bool:
        legal = self.board.legal_moves(self.turn)
        if not any(m.from_sq == move.from_sq and m.to_sq == move.to_sq for m in legal):
            return False

        if self._history_index < len(self._history) - 1:
            self.move_history = self.move_history[:self._history_index]
        self.move_history.append(move)

        r_from, c_from = move.from_sq
        r_to, c_to = move.to_sq
        piece = self.board.grid[r_from][c_from]
        self.board.grid[r_to][c_to] = piece
        self.board.grid[r_from][c_from] = None

        if piece is not None and piece.kind == "P" and move.promotion:
            self.board.grid[r_to][c_to] = Piece(move.promotion, piece.color)

        self.turn = 'b' if self.turn == 'w' else 'w'
        self._king_check_valid = False
        self.record_position()
        return True

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

    def to_state(self):
        return {
            "rows": self.board.rows,
            "cols": self.board.cols,
            "turn": self.turn,
            "position_index": self._history_index,
            "move_history": [self._serialize_move(move) for move in self.move_history],
            "history": [
                {
                    "turn": snapshot.turn,
                    "grid": [
                        [self._serialize_piece(piece) for piece in row]
                        for row in snapshot.grid
                    ],
                }
                for snapshot in self._history
            ],
        }

    @classmethod
    def from_state(cls, state):
        rows = state["rows"]
        cols = state["cols"]
        game = cls(rows=rows, cols=cols)
        game.turn = state["turn"]
        game.move_history = [
            cls._deserialize_move(move_data) for move_data in state["move_history"]
        ]
        game._history = [
            GameSnapshot(
                turn=snapshot_data["turn"],
                grid=[
                    [cls._deserialize_piece(piece_data) for piece_data in row]
                    for row in snapshot_data["grid"]
                ],
            )
            for snapshot_data in state["history"]
        ]
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
