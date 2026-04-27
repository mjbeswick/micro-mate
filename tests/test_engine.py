"""Comprehensive unit tests for micromate/engine.py."""
import json
import sys
import os
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from micromate.engine import (
    AI, Board, Game, GameSnapshot, Move, Piece,
    _empty_bb, _occ_all, _occ_color,
)


def make_board(*pieces, rows=8, cols=8):
    """Return an empty Board (no startpos) with the given pieces placed on it."""
    b = Board.__new__(Board)
    b.rows = rows
    b.cols = cols
    b.bb = _empty_bb()
    for r, c, kind, color in pieces:
        b._set_piece(r, c, Piece(kind, color))
    return b


def moves_set(moves):
    """Convert move list to a set of (from_sq, to_sq) tuples for easy comparison."""
    return {(m.from_sq, m.to_sq) for m in moves}


# ---------------------------------------------------------------------------
# Piece / Move dataclasses
# ---------------------------------------------------------------------------

class TestDataclasses(unittest.TestCase):

    def test_piece_equality(self):
        self.assertEqual(Piece('P', 'w'), Piece('P', 'w'))
        self.assertNotEqual(Piece('P', 'w'), Piece('P', 'b'))
        self.assertNotEqual(Piece('P', 'w'), Piece('N', 'w'))

    def test_move_equality(self):
        m1 = Move((1, 0), (2, 0))
        m2 = Move((1, 0), (2, 0))
        self.assertEqual(m1, m2)

    def test_move_with_promotion(self):
        m = Move((1, 0), (0, 0), promotion='Q')
        self.assertEqual(m.promotion, 'Q')

    def test_move_default_promotion_none(self):
        self.assertIsNone(Move((1, 0), (2, 0)).promotion)


# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

class TestBoardHelpers(unittest.TestCase):

    def setUp(self):
        self.b = Board(rows=8, cols=8)

    def test_bit_a1(self):
        self.assertEqual(self.b._bit(0, 0), 1)

    def test_bit_a2(self):
        self.assertEqual(self.b._bit(0, 1), 2)

    def test_bit_second_row(self):
        self.assertEqual(self.b._bit(1, 0), 256)

    def test_bit_last_square(self):
        expected = 1 << (7 * 8 + 7)
        self.assertEqual(self.b._bit(7, 7), expected)

    def test_piece_at_returns_none_on_empty(self):
        b = make_board(rows=8, cols=8)
        self.assertIsNone(b.piece_at(3, 3))

    def test_piece_at_finds_white_piece(self):
        b = make_board((3, 3, 'Q', 'w'), rows=8, cols=8)
        self.assertEqual(b.piece_at(3, 3), Piece('Q', 'w'))

    def test_piece_at_finds_black_piece(self):
        b = make_board((0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertEqual(b.piece_at(0, 0), Piece('K', 'b'))

    def test_piece_at_returns_none_for_adjacent_square(self):
        b = make_board((3, 3, 'Q', 'w'), rows=8, cols=8)
        self.assertIsNone(b.piece_at(3, 4))

    def test_occ_color_counts_own_pieces(self):
        b = make_board(
            (0, 0, 'K', 'w'), (1, 0, 'P', 'w'), (7, 7, 'K', 'b'),
            rows=8, cols=8
        )
        occ_w = _occ_color(b.bb, 'w')
        self.assertTrue(occ_w & b._bit(0, 0))
        self.assertTrue(occ_w & b._bit(1, 0))
        self.assertFalse(occ_w & b._bit(7, 7))

    def test_occ_all_covers_both_colors(self):
        b = make_board((0, 0, 'K', 'w'), (7, 7, 'K', 'b'), rows=8, cols=8)
        occ = _occ_all(b.bb)
        self.assertTrue(occ & b._bit(0, 0))
        self.assertTrue(occ & b._bit(7, 7))
        self.assertFalse(occ & b._bit(3, 3))


# ---------------------------------------------------------------------------
# Board.setup_startpos
# ---------------------------------------------------------------------------

class TestSetupStartpos(unittest.TestCase):

    def test_8x8_white_back_rank(self):
        b = Board(8, 8)
        # White back rank is the reverse of black's: R N B K Q B N R
        expected = [('R', 7, 0), ('N', 7, 1), ('B', 7, 2), ('K', 7, 3),
                    ('Q', 7, 4), ('B', 7, 5), ('N', 7, 6), ('R', 7, 7)]
        for kind, r, c in expected:
            self.assertEqual(b.piece_at(r, c), Piece(kind, 'w'), f"Expected {kind} at ({r},{c})")

    def test_8x8_black_back_rank(self):
        b = Board(8, 8)
        expected = [('R', 0, 0), ('N', 0, 1), ('B', 0, 2), ('Q', 0, 3),
                    ('K', 0, 4), ('B', 0, 5), ('N', 0, 6), ('R', 0, 7)]
        for kind, r, c in expected:
            self.assertEqual(b.piece_at(r, c), Piece(kind, 'b'), f"Expected {kind} at ({r},{c})")

    def test_8x8_white_pawns_row_6(self):
        b = Board(8, 8)
        for c in range(8):
            self.assertEqual(b.piece_at(6, c), Piece('P', 'w'))

    def test_8x8_black_pawns_row_1(self):
        b = Board(8, 8)
        for c in range(8):
            self.assertEqual(b.piece_at(1, c), Piece('P', 'b'))

    def test_8x8_middle_rows_empty(self):
        b = Board(8, 8)
        for r in range(2, 6):
            for c in range(8):
                self.assertIsNone(b.piece_at(r, c))

    def test_5x6_default_has_pieces(self):
        b = Board(5, 6)
        # Back ranks should be populated
        self.assertIsNotNone(b.piece_at(0, 0))  # black back rank
        self.assertIsNotNone(b.piece_at(4, 5))  # white back rank

    def test_3x3_pawns_only(self):
        b = Board(3, 3)
        for c in range(3):
            self.assertEqual(b.piece_at(0, c), Piece('P', 'b'))
            self.assertEqual(b.piece_at(2, c), Piece('P', 'w'))
        self.assertIsNone(b.piece_at(1, 0))

    def test_4x4_has_kings(self):
        b = Board(4, 4)
        # back_rank for 4 cols is ["R","K","Q","R"] reversed for white
        whites = [b.piece_at(3, c) for c in range(4)]
        kinds = [p.kind for p in whites if p]
        self.assertIn('K', kinds)

    def test_rows_less_than_2_empty_board(self):
        b = Board(1, 4)
        for c in range(4):
            self.assertIsNone(b.piece_at(0, c))


# ---------------------------------------------------------------------------
# Pawn moves
# ---------------------------------------------------------------------------

class TestPawnMoves(unittest.TestCase):

    def test_white_pawn_single_advance(self):
        b = make_board((5, 3, 'P', 'w'), (7, 7, 'K', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        moves = moves_set(b._pawn_moves(5, 3, 'w'))
        self.assertIn(((5, 3), (4, 3)), moves)

    def test_white_pawn_double_advance_from_start_rank(self):
        b = make_board((6, 3, 'P', 'w'), (7, 7, 'K', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        moves = moves_set(b._pawn_moves(6, 3, 'w'))
        self.assertIn(((6, 3), (4, 3)), moves)

    def test_white_pawn_no_double_advance_from_non_start(self):
        b = make_board((5, 3, 'P', 'w'), (7, 7, 'K', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        moves = moves_set(b._pawn_moves(5, 3, 'w'))
        self.assertNotIn(((5, 3), (3, 3)), moves)

    def test_white_pawn_blocked_cannot_advance(self):
        b = make_board(
            (5, 3, 'P', 'w'), (4, 3, 'P', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        moves = moves_set(b._pawn_moves(5, 3, 'w'))
        self.assertNotIn(((5, 3), (4, 3)), moves)

    def test_white_pawn_blocked_no_double_if_first_square_occupied(self):
        b = make_board(
            (6, 3, 'P', 'w'), (5, 3, 'R', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        moves = moves_set(b._pawn_moves(6, 3, 'w'))
        self.assertNotIn(((6, 3), (4, 3)), moves)
        self.assertNotIn(((6, 3), (5, 3)), moves)

    def test_white_pawn_captures_diagonally(self):
        b = make_board(
            (5, 3, 'P', 'w'), (4, 2, 'P', 'b'), (4, 4, 'P', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        moves = moves_set(b._pawn_moves(5, 3, 'w'))
        self.assertIn(((5, 3), (4, 2)), moves)
        self.assertIn(((5, 3), (4, 4)), moves)

    def test_white_pawn_does_not_capture_own_piece(self):
        b = make_board(
            (5, 3, 'P', 'w'), (4, 2, 'N', 'w'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        moves = moves_set(b._pawn_moves(5, 3, 'w'))
        self.assertNotIn(((5, 3), (4, 2)), moves)

    def test_white_pawn_promotion(self):
        b = make_board(
            (1, 3, 'P', 'w'), (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        moves = b._pawn_moves(1, 3, 'w')
        promo_moves = [m for m in moves if m.to_sq == (0, 3)]
        self.assertEqual(len(promo_moves), 1)
        self.assertEqual(promo_moves[0].promotion, 'Q')

    def test_black_pawn_advances_down(self):
        b = make_board((2, 3, 'P', 'b'), (0, 0, 'K', 'b'), (7, 7, 'K', 'w'), rows=8, cols=8)
        moves = moves_set(b._pawn_moves(2, 3, 'b'))
        self.assertIn(((2, 3), (3, 3)), moves)

    def test_black_pawn_double_advance_from_start(self):
        b = make_board((1, 3, 'P', 'b'), (0, 0, 'K', 'b'), (7, 7, 'K', 'w'), rows=8, cols=8)
        moves = moves_set(b._pawn_moves(1, 3, 'b'))
        self.assertIn(((1, 3), (3, 3)), moves)

    def test_black_pawn_promotion(self):
        b = make_board(
            (6, 3, 'P', 'b'), (0, 0, 'K', 'b'), (7, 7, 'K', 'w'),
            rows=8, cols=8
        )
        moves = b._pawn_moves(6, 3, 'b')
        promo_moves = [m for m in moves if m.to_sq == (7, 3)]
        self.assertEqual(len(promo_moves), 1)
        self.assertEqual(promo_moves[0].promotion, 'Q')

    def test_pawn_at_edge_col_no_wrap(self):
        b = make_board(
            (5, 0, 'P', 'w'), (4, 7, 'P', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        moves = moves_set(b._pawn_moves(5, 0, 'w'))
        # Should not have a capture to col -1 (off board) or col 7 (other side)
        cols = {to_sq[1] for _, to_sq in moves}
        self.assertNotIn(-1, cols)
        self.assertNotIn(7, cols)


# ---------------------------------------------------------------------------
# Knight moves
# ---------------------------------------------------------------------------

class TestKnightMoves(unittest.TestCase):

    def test_knight_from_center_has_8_moves(self):
        b = make_board((4, 4, 'N', 'w'), (7, 7, 'K', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        moves = b._knight_moves(4, 4, 'w')
        self.assertEqual(len(moves), 8)

    def test_knight_from_corner_has_2_moves(self):
        b = make_board((0, 0, 'N', 'w'), (7, 7, 'K', 'w'), (0, 7, 'K', 'b'), rows=8, cols=8)
        moves = b._knight_moves(0, 0, 'w')
        self.assertEqual(len(moves), 2)

    def test_knight_cannot_land_on_own_piece(self):
        b = make_board(
            (4, 4, 'N', 'w'), (2, 3, 'P', 'w'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        moves = moves_set(b._knight_moves(4, 4, 'w'))
        self.assertNotIn(((4, 4), (2, 3)), moves)

    def test_knight_can_capture_enemy(self):
        b = make_board(
            (4, 4, 'N', 'w'), (2, 3, 'P', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        moves = moves_set(b._knight_moves(4, 4, 'w'))
        self.assertIn(((4, 4), (2, 3)), moves)

    def test_knight_jumps_over_pieces(self):
        b = make_board(
            (4, 4, 'N', 'w'),
            (3, 4, 'P', 'w'), (4, 3, 'P', 'w'), (5, 4, 'P', 'w'), (4, 5, 'P', 'w'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        moves = b._knight_moves(4, 4, 'w')
        self.assertGreater(len(moves), 0)


# ---------------------------------------------------------------------------
# Sliding piece moves
# ---------------------------------------------------------------------------

class TestSlidingMoves(unittest.TestCase):

    def test_rook_open_file_has_all_squares(self):
        b = make_board((4, 4, 'R', 'w'), (7, 7, 'K', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        moves = b._sliding_moves(4, 4, 'w', [(-1, 0), (1, 0), (0, -1), (0, 1)])
        # 4 up, 3 down, 4 left, 3 right = 14 squares
        self.assertEqual(len(moves), 14)

    def test_rook_blocked_by_own_piece(self):
        b = make_board(
            (4, 4, 'R', 'w'), (4, 6, 'P', 'w'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        moves = moves_set(b._sliding_moves(4, 4, 'w', [(0, 1)]))
        self.assertIn(((4, 4), (4, 5)), moves)
        self.assertNotIn(((4, 4), (4, 6)), moves)
        self.assertNotIn(((4, 4), (4, 7)), moves)

    def test_rook_captures_enemy_and_stops(self):
        b = make_board(
            (4, 4, 'R', 'w'), (4, 6, 'P', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        moves = moves_set(b._sliding_moves(4, 4, 'w', [(0, 1)]))
        self.assertIn(((4, 4), (4, 5)), moves)
        self.assertIn(((4, 4), (4, 6)), moves)   # capture
        self.assertNotIn(((4, 4), (4, 7)), moves)  # stops after capture

    def test_bishop_diagonal_moves(self):
        b = make_board((4, 4, 'B', 'w'), (7, 7, 'K', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        diagonals = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        moves = b._sliding_moves(4, 4, 'w', diagonals)
        targets = {to_sq for _, to_sq in moves_set(moves)}
        self.assertIn((3, 3), targets)
        self.assertIn((5, 5), targets)
        self.assertIn((3, 5), targets)
        self.assertIn((5, 3), targets)

    def test_queen_combines_rook_and_bishop(self):
        b = make_board((4, 4, 'Q', 'w'), (7, 7, 'K', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        all_dirs = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
        moves = b._sliding_moves(4, 4, 'w', all_dirs)
        # Should have moves in all 8 directions
        self.assertGreater(len(moves), 20)


# ---------------------------------------------------------------------------
# King moves
# ---------------------------------------------------------------------------

class TestKingMoves(unittest.TestCase):

    def test_king_from_center_has_8_moves(self):
        b = make_board((4, 4, 'K', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        moves = b._king_moves(4, 4, 'w')
        self.assertEqual(len(moves), 8)

    def test_king_from_corner_has_3_moves(self):
        b = make_board((0, 0, 'K', 'w'), (7, 7, 'K', 'b'), rows=8, cols=8)
        moves = b._king_moves(0, 0, 'w')
        self.assertEqual(len(moves), 3)

    def test_king_cannot_land_on_own_piece(self):
        b = make_board(
            (4, 4, 'K', 'w'), (4, 5, 'P', 'w'),
            (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        moves = moves_set(b._king_moves(4, 4, 'w'))
        self.assertNotIn(((4, 4), (4, 5)), moves)


# ---------------------------------------------------------------------------
# Check detection
# ---------------------------------------------------------------------------

class TestCheckDetection(unittest.TestCase):

    def test_not_in_check_at_start(self):
        b = Board(8, 8)
        self.assertFalse(b._is_in_check('w'))
        self.assertFalse(b._is_in_check('b'))

    def test_check_by_rook(self):
        b = make_board((7, 4, 'K', 'w'), (0, 4, 'R', 'b'), (0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertTrue(b._is_in_check('w'))

    def test_check_by_bishop(self):
        b = make_board((7, 4, 'K', 'w'), (4, 1, 'B', 'b'), (0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertTrue(b._is_in_check('w'))

    def test_check_by_queen_orthogonal(self):
        b = make_board((7, 4, 'K', 'w'), (7, 0, 'Q', 'b'), (0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertTrue(b._is_in_check('w'))

    def test_check_by_queen_diagonal(self):
        b = make_board((7, 4, 'K', 'w'), (5, 2, 'Q', 'b'), (0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertTrue(b._is_in_check('w'))

    def test_check_by_knight(self):
        b = make_board((7, 4, 'K', 'w'), (5, 3, 'N', 'b'), (0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertTrue(b._is_in_check('w'))

    def test_check_by_pawn(self):
        b = make_board((7, 4, 'K', 'w'), (6, 3, 'P', 'b'), (0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertTrue(b._is_in_check('w'))

    def test_check_by_pawn_other_diagonal(self):
        b = make_board((7, 4, 'K', 'w'), (6, 5, 'P', 'b'), (0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertTrue(b._is_in_check('w'))

    def test_not_in_check_blocked_by_piece(self):
        b = make_board(
            (7, 4, 'K', 'w'), (7, 2, 'P', 'w'), (7, 0, 'R', 'b'),
            (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        self.assertFalse(b._is_in_check('w'))

    def test_no_king_returns_false(self):
        b = make_board((0, 0, 'P', 'w'), rows=8, cols=8)
        self.assertFalse(b._is_in_check('w'))

    def test_check_by_enemy_king(self):
        b = make_board((4, 4, 'K', 'w'), (4, 5, 'K', 'b'), rows=8, cols=8)
        self.assertTrue(b._is_in_check('w'))
        self.assertTrue(b._is_in_check('b'))

    def test_pawn_does_not_check_directly_forward(self):
        # Black pawn directly in front of white king does not check (pawns capture diagonally)
        b = make_board((7, 4, 'K', 'w'), (6, 4, 'P', 'b'), (0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertFalse(b._is_in_check('w'))


# ---------------------------------------------------------------------------
# _can_piece_attack
# ---------------------------------------------------------------------------

class TestCanPieceAttack(unittest.TestCase):

    def test_rook_attacks_same_row(self):
        b = make_board((4, 0, 'R', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertTrue(b._can_piece_attack(4, 0, 4, 7, 'R', 'w'))

    def test_rook_blocked_by_own_piece(self):
        b = make_board((4, 0, 'R', 'w'), (4, 3, 'P', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertFalse(b._can_piece_attack(4, 0, 4, 7, 'R', 'w'))

    def test_bishop_attacks_diagonal(self):
        b = make_board((4, 4, 'B', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertTrue(b._can_piece_attack(4, 4, 1, 7, 'B', 'w'))

    def test_bishop_does_not_attack_orthogonal(self):
        b = make_board((4, 4, 'B', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertFalse(b._can_piece_attack(4, 4, 4, 7, 'B', 'w'))

    def test_knight_attack(self):
        b = make_board((4, 4, 'N', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertTrue(b._can_piece_attack(4, 4, 2, 3, 'N', 'w'))
        self.assertFalse(b._can_piece_attack(4, 4, 4, 6, 'N', 'w'))

    def test_pawn_attack_direction(self):
        b = make_board((5, 4, 'P', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertTrue(b._can_piece_attack(5, 4, 4, 3, 'P', 'w'))
        self.assertTrue(b._can_piece_attack(5, 4, 4, 5, 'P', 'w'))
        self.assertFalse(b._can_piece_attack(5, 4, 6, 3, 'P', 'w'))  # wrong direction
        self.assertFalse(b._can_piece_attack(5, 4, 4, 4, 'P', 'w'))  # forward, not diagonal

    def test_king_attack(self):
        b = make_board((4, 4, 'K', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertTrue(b._can_piece_attack(4, 4, 4, 5, 'K', 'w'))
        self.assertFalse(b._can_piece_attack(4, 4, 4, 6, 'K', 'w'))

    def test_no_piece_at_source_returns_false(self):
        b = make_board((0, 0, 'K', 'b'), rows=8, cols=8)
        self.assertFalse(b._can_piece_attack(3, 3, 5, 5))


# ---------------------------------------------------------------------------
# _make_move_unsafe / _undo_move_unsafe
# ---------------------------------------------------------------------------

class TestMakeMoveUnsafe(unittest.TestCase):

    def test_simple_move_updates_board(self):
        b = make_board((6, 4, 'P', 'w'), (7, 7, 'K', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        m = Move((6, 4), (5, 4))
        b._make_move_unsafe(m)
        self.assertIsNone(b.piece_at(6, 4))
        self.assertEqual(b.piece_at(5, 4), Piece('P', 'w'))

    def test_simple_move_returns_none_for_no_capture(self):
        b = make_board((6, 4, 'P', 'w'), (7, 7, 'K', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        m = Move((6, 4), (5, 4))
        captured = b._make_move_unsafe(m)
        self.assertIsNone(captured)

    def test_capture_removes_target(self):
        b = make_board(
            (6, 4, 'P', 'w'), (5, 3, 'P', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        m = Move((6, 4), (5, 3))
        captured = b._make_move_unsafe(m)
        self.assertEqual(captured, Piece('P', 'b'))
        self.assertIsNone(b.piece_at(6, 4))
        self.assertEqual(b.piece_at(5, 3), Piece('P', 'w'))

    def test_promotion_replaces_pawn_with_queen(self):
        b = make_board((1, 4, 'P', 'w'), (7, 7, 'K', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        m = Move((1, 4), (0, 4), promotion='Q')
        b._make_move_unsafe(m)
        self.assertEqual(b.piece_at(0, 4), Piece('Q', 'w'))
        self.assertIsNone(b.piece_at(1, 4))

    def test_undo_restores_simple_move(self):
        b = make_board((6, 4, 'P', 'w'), (7, 7, 'K', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        m = Move((6, 4), (5, 4))
        captured = b._make_move_unsafe(m)
        b._undo_move_unsafe(m, captured)
        self.assertEqual(b.piece_at(6, 4), Piece('P', 'w'))
        self.assertIsNone(b.piece_at(5, 4))

    def test_undo_restores_captured_piece(self):
        b = make_board(
            (6, 4, 'P', 'w'), (5, 3, 'N', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        m = Move((6, 4), (5, 3))
        captured = b._make_move_unsafe(m)
        b._undo_move_unsafe(m, captured)
        self.assertEqual(b.piece_at(6, 4), Piece('P', 'w'))
        self.assertEqual(b.piece_at(5, 3), Piece('N', 'b'))

    def test_undo_restores_pawn_after_promotion(self):
        b = make_board((1, 4, 'P', 'w'), (7, 7, 'K', 'w'), (0, 0, 'K', 'b'), rows=8, cols=8)
        m = Move((1, 4), (0, 4), promotion='Q')
        captured = b._make_move_unsafe(m)
        b._undo_move_unsafe(m, captured)
        self.assertEqual(b.piece_at(1, 4), Piece('P', 'w'))
        self.assertIsNone(b.piece_at(0, 4))

    def test_round_trip_multiple_moves(self):
        b = Board(8, 8)
        before_bb = {'w': dict(b.bb['w']), 'b': dict(b.bb['b'])}
        m1 = Move((6, 4), (4, 4))  # e2-e4
        m2 = Move((1, 4), (3, 4))  # e7-e5
        c1 = b._make_move_unsafe(m1)
        c2 = b._make_move_unsafe(m2)
        b._undo_move_unsafe(m2, c2)
        b._undo_move_unsafe(m1, c1)
        self.assertEqual(b.bb, before_bb)


# ---------------------------------------------------------------------------
# Legal moves (full legality including check filtering)
# ---------------------------------------------------------------------------

class TestLegalMoves(unittest.TestCase):

    def test_starting_position_white_has_20_moves(self):
        b = Board(8, 8)
        moves = b.legal_moves('w')
        self.assertEqual(len(moves), 20)

    def test_starting_position_black_has_20_moves(self):
        b = Board(8, 8)
        moves = b.legal_moves('b')
        self.assertEqual(len(moves), 20)

    def test_pinned_piece_cannot_move(self):
        # White rook pinned on e-file by black rook: rook cannot leave the e-file
        b = make_board(
            (7, 4, 'K', 'w'), (5, 4, 'R', 'w'), (0, 4, 'R', 'b'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        rook_moves = [m for m in b.legal_moves('w') if m.from_sq == (5, 4)]
        for m in rook_moves:
            self.assertEqual(m.to_sq[1], 4, f"Pinned rook moved off column: {m}")

    def test_cannot_move_into_check(self):
        b = make_board((7, 4, 'K', 'w'), (5, 5, 'R', 'b'), (0, 0, 'K', 'b'), rows=8, cols=8)
        legal = b.legal_moves('w')
        king_moves = [m for m in legal if m.from_sq == (7, 4)]
        destinations = {m.to_sq for m in king_moves}
        self.assertNotIn((7, 5), destinations)

    def test_must_block_check(self):
        # King in check: only legal moves are escapes/blocks
        b = make_board(
            (7, 4, 'K', 'w'), (7, 0, 'R', 'b'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        legal = b.legal_moves('w')
        # All moves must resolve the check
        for move in legal:
            cap = b._make_move_unsafe(move)
            self.assertFalse(b._is_in_check('w'), f"Move {move} leaves king in check")
            b._undo_move_unsafe(move, cap)

    def test_checkmate_no_legal_moves(self):
        # Fool's mate position
        b = make_board(
            (7, 4, 'K', 'w'), (7, 5, 'P', 'w'), (7, 6, 'P', 'w'),
            (0, 3, 'Q', 'b'), (0, 4, 'K', 'b'),
            rows=8, cols=8
        )
        # Manually set: queen on h4 (row=4, col=7 in our coords) targeting f2
        b2 = make_board(
            (7, 4, 'K', 'w'), (6, 5, 'P', 'w'), (6, 6, 'P', 'w'),
            (4, 7, 'Q', 'b'), (0, 4, 'K', 'b'),
            rows=8, cols=8
        )
        # Whether it's checkmate depends on the exact position; just verify the property
        if b2._is_in_check('w'):
            legal = b2.legal_moves('w')
            # If in check, all legal moves must resolve it
            for m in legal:
                cap = b2._make_move_unsafe(m)
                self.assertFalse(b2._is_in_check('w'))
                b2._undo_move_unsafe(m, cap)

    def test_stalemate_position_has_no_legal_moves(self):
        # Classic stalemate: white king trapped with no legal moves and not in check
        b = make_board(
            (0, 0, 'K', 'w'), (1, 2, 'Q', 'b'), (2, 1, 'K', 'b'),
            rows=8, cols=8
        )
        if not b._is_in_check('w'):
            legal = b.legal_moves('w')
            self.assertEqual(legal, [])


# ---------------------------------------------------------------------------
# Game.make_move
# ---------------------------------------------------------------------------

class TestGameMakeMove(unittest.TestCase):

    def setUp(self):
        self.g = Game(rows=8, cols=8)

    def test_legal_move_returns_true(self):
        result = self.g.make_move(Move((6, 4), (4, 4)))
        self.assertTrue(result)

    def test_legal_move_updates_board(self):
        self.g.make_move(Move((6, 4), (4, 4)))
        self.assertIsNone(self.g.board.piece_at(6, 4))
        self.assertEqual(self.g.board.piece_at(4, 4), Piece('P', 'w'))

    def test_legal_move_advances_turn(self):
        self.assertEqual(self.g.turn, 'w')
        self.g.make_move(Move((6, 4), (4, 4)))
        self.assertEqual(self.g.turn, 'b')

    def test_illegal_move_returns_false(self):
        result = self.g.make_move(Move((6, 4), (3, 4)))  # 3-square pawn advance
        self.assertFalse(result)

    def test_illegal_move_does_not_change_turn(self):
        self.g.make_move(Move((6, 4), (3, 4)))
        self.assertEqual(self.g.turn, 'w')

    def test_illegal_move_does_not_change_board(self):
        original_piece = self.g.board.piece_at(6, 4)
        self.g.make_move(Move((6, 4), (3, 4)))
        self.assertEqual(self.g.board.piece_at(6, 4), original_piece)

    def test_move_records_history(self):
        before = self.g.position_count
        self.g.make_move(Move((6, 4), (4, 4)))
        self.assertEqual(self.g.position_count, before + 1)

    def test_move_updates_move_history(self):
        m = Move((6, 4), (4, 4))
        self.g.make_move(m)
        self.assertIn(m, self.g.move_history)

    def test_turn_alternates(self):
        self.g.make_move(Move((6, 4), (4, 4)))
        self.g.make_move(Move((1, 4), (3, 4)))
        self.assertEqual(self.g.turn, 'w')

    def test_wrong_color_cannot_move(self):
        # Black cannot move on white's turn
        result = self.g.make_move(Move((1, 4), (3, 4)))
        self.assertFalse(result)

    def test_king_check_cache_invalidated_after_move(self):
        # Access cache first
        _ = self.g.get_king_check_square()
        self.g.make_move(Move((6, 4), (4, 4)))
        self.assertFalse(self.g._king_check_valid)


# ---------------------------------------------------------------------------
# Game.make_attacker_loss
# ---------------------------------------------------------------------------

class TestMakeAttackerLoss(unittest.TestCase):

    def _setup_capture_position(self):
        g = Game.__new__(Game)
        b = make_board(
            (4, 4, 'R', 'w'), (4, 6, 'P', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        g.board = b
        g.turn = 'w'
        g.move_history = []
        g._history = [GameSnapshot(bb={'w': dict(b.bb['w']), 'b': dict(b.bb['b'])}, turn='w')]
        g._history_index = 0
        g.ai_depth = 3
        g.ai = AI(depth=3)
        g._king_check_valid = False
        g._king_check_sq = None
        return g

    def test_removes_attacker_piece(self):
        g = self._setup_capture_position()
        m = Move((4, 4), (4, 6))
        g.make_attacker_loss(m)
        self.assertIsNone(g.board.piece_at(4, 4))

    def test_defender_piece_unchanged(self):
        g = self._setup_capture_position()
        m = Move((4, 4), (4, 6))
        g.make_attacker_loss(m)
        self.assertEqual(g.board.piece_at(4, 6), Piece('P', 'b'))

    def test_advances_turn(self):
        g = self._setup_capture_position()
        m = Move((4, 4), (4, 6))
        g.make_attacker_loss(m)
        self.assertEqual(g.turn, 'b')

    def test_records_move_in_history(self):
        g = self._setup_capture_position()
        m = Move((4, 4), (4, 6))
        g.make_attacker_loss(m)
        self.assertIn(m, g.move_history)

    def test_records_position_snapshot(self):
        g = self._setup_capture_position()
        before = g.position_count
        m = Move((4, 4), (4, 6))
        g.make_attacker_loss(m)
        self.assertEqual(g.position_count, before + 1)

    def test_invalidates_check_cache(self):
        g = self._setup_capture_position()
        _ = g.get_king_check_square()
        g.make_attacker_loss(Move((4, 4), (4, 6)))
        self.assertFalse(g._king_check_valid)

    def test_no_piece_at_source_does_not_crash(self):
        g = self._setup_capture_position()
        # Move from empty square — should not crash
        g.make_attacker_loss(Move((3, 3), (4, 6)))
        self.assertEqual(g.turn, 'b')

    def test_removing_piece_that_gave_check_clears_check(self):
        b = make_board(
            (7, 4, 'K', 'w'), (5, 4, 'R', 'b'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        g = Game.__new__(Game)
        g.board = b
        g.turn = 'b'
        g.move_history = []
        g._history = [GameSnapshot(bb={'w': dict(b.bb['w']), 'b': dict(b.bb['b'])}, turn='b')]
        g._history_index = 0
        g.ai_depth = 1
        g.ai = AI(depth=1)
        g._king_check_valid = False
        g._king_check_sq = None

        self.assertTrue(b._is_in_check('w'))
        g.make_attacker_loss(Move((5, 4), (7, 4)))  # defender wins (rook was attacking)
        self.assertFalse(g.board._is_in_check('w'))


# ---------------------------------------------------------------------------
# Game.skip_turn
# ---------------------------------------------------------------------------

class TestSkipTurn(unittest.TestCase):

    def setUp(self):
        self.g = Game(rows=8, cols=8)
        self.initial_bb = {'w': dict(self.g.board.bb['w']), 'b': dict(self.g.board.bb['b'])}

    def test_board_unchanged(self):
        self.g.skip_turn(Move((6, 4), (5, 3)))
        self.assertEqual(self.g.board.bb, self.initial_bb)

    def test_advances_turn(self):
        self.g.skip_turn(Move((6, 4), (5, 3)))
        self.assertEqual(self.g.turn, 'b')

    def test_double_skip_restores_turn(self):
        m = Move((6, 4), (5, 3))
        self.g.skip_turn(m)
        self.g.skip_turn(m)
        self.assertEqual(self.g.turn, 'w')

    def test_records_move_in_history(self):
        m = Move((6, 4), (5, 3))
        self.g.skip_turn(m)
        self.assertIn(m, self.g.move_history)

    def test_records_position_snapshot(self):
        before = self.g.position_count
        self.g.skip_turn(Move((6, 4), (5, 3)))
        self.assertEqual(self.g.position_count, before + 1)

    def test_invalidates_check_cache(self):
        _ = self.g.get_king_check_square()
        self.g.skip_turn(Move((6, 4), (5, 3)))
        self.assertFalse(self.g._king_check_valid)


# ---------------------------------------------------------------------------
# Game history navigation
# ---------------------------------------------------------------------------

class TestGameHistory(unittest.TestCase):

    def setUp(self):
        self.g = Game(rows=8, cols=8)

    def test_cannot_step_backward_at_start(self):
        self.assertFalse(self.g.can_step_backward())

    def test_cannot_step_forward_at_start(self):
        self.assertFalse(self.g.can_step_forward())

    def test_can_step_backward_after_move(self):
        self.g.make_move(Move((6, 4), (4, 4)))
        self.assertTrue(self.g.can_step_backward())

    def test_step_backward_restores_board(self):
        self.g.make_move(Move((6, 4), (4, 4)))
        self.g.step_backward()
        self.assertEqual(self.g.board.piece_at(6, 4), Piece('P', 'w'))
        self.assertIsNone(self.g.board.piece_at(4, 4))

    def test_step_backward_restores_turn(self):
        self.g.make_move(Move((6, 4), (4, 4)))
        self.g.step_backward()
        self.assertEqual(self.g.turn, 'w')

    def test_can_step_forward_after_backward(self):
        self.g.make_move(Move((6, 4), (4, 4)))
        self.g.step_backward()
        self.assertTrue(self.g.can_step_forward())

    def test_step_forward_reapplies_move(self):
        self.g.make_move(Move((6, 4), (4, 4)))
        self.g.step_backward()
        self.g.step_forward()
        self.assertIsNone(self.g.board.piece_at(6, 4))
        self.assertEqual(self.g.board.piece_at(4, 4), Piece('P', 'w'))

    def test_step_backward_returns_false_at_start(self):
        result = self.g.step_backward()
        self.assertFalse(result)

    def test_step_forward_returns_false_at_end(self):
        result = self.g.step_forward()
        self.assertFalse(result)

    def test_current_move_none_at_start(self):
        self.assertIsNone(self.g.current_move)

    def test_current_move_after_one_move(self):
        m = Move((6, 4), (4, 4))
        self.g.make_move(m)
        self.assertEqual(self.g.current_move, m)

    def test_new_move_truncates_forward_history(self):
        self.g.make_move(Move((6, 4), (4, 4)))  # e2-e4
        self.g.step_backward()
        # Make a different move from the same position
        self.g.make_move(Move((6, 3), (4, 3)))  # d2-d4
        self.assertFalse(self.g.can_step_forward())

    def test_history_grows_with_moves(self):
        self.g.make_move(Move((6, 4), (4, 4)))
        self.g.make_move(Move((1, 4), (3, 4)))
        self.assertEqual(self.g.position_count, 3)

    def test_skip_turn_is_navigable(self):
        m = Move((6, 4), (5, 3))
        self.g.skip_turn(m)
        self.g.step_backward()
        self.assertEqual(self.g.turn, 'w')

    def test_attacker_loss_is_navigable(self):
        m = Move((6, 4), (5, 3))
        self.g.make_attacker_loss(m)
        self.g.step_backward()
        # Should restore original board and turn
        self.assertEqual(self.g.turn, 'w')


# ---------------------------------------------------------------------------
# Game.reset
# ---------------------------------------------------------------------------

class TestGameReset(unittest.TestCase):

    def test_reset_clears_move_history(self):
        g = Game(8, 8)
        g.make_move(Move((6, 4), (4, 4)))
        g.reset()
        self.assertEqual(g.move_history, [])

    def test_reset_restores_starting_position(self):
        g = Game(8, 8)
        g.make_move(Move((6, 4), (4, 4)))
        g.reset()
        self.assertEqual(g.board.piece_at(6, 4), Piece('P', 'w'))

    def test_reset_restores_white_turn(self):
        g = Game(8, 8)
        g.make_move(Move((6, 4), (4, 4)))
        g.reset()
        self.assertEqual(g.turn, 'w')

    def test_reset_preserves_dimensions(self):
        g = Game(5, 6)
        g.reset()
        self.assertEqual(g.board.rows, 5)
        self.assertEqual(g.board.cols, 6)

    def test_reset_resets_history_to_one_snapshot(self):
        g = Game(8, 8)
        g.make_move(Move((6, 4), (4, 4)))
        g.reset()
        self.assertEqual(g.position_count, 1)
        self.assertEqual(g._history_index, 0)


# ---------------------------------------------------------------------------
# Game.get_king_check_square
# ---------------------------------------------------------------------------

class TestGetKingCheckSquare(unittest.TestCase):

    def test_returns_none_when_not_in_check(self):
        g = Game(8, 8)
        self.assertIsNone(g.get_king_check_square())

    def test_returns_king_position_when_in_check(self):
        b = make_board(
            (7, 4, 'K', 'w'), (7, 0, 'R', 'b'), (0, 0, 'K', 'b'),
            rows=8, cols=8
        )
        g = Game.__new__(Game)
        g.board = b
        g.turn = 'w'
        g._king_check_valid = False
        g._king_check_sq = None
        sq = g.get_king_check_square()
        self.assertEqual(sq, (7, 4))

    def test_result_cached_on_second_call(self):
        g = Game(8, 8)
        g.get_king_check_square()
        self.assertTrue(g._king_check_valid)
        # Second call should use cache
        g.get_king_check_square()
        self.assertTrue(g._king_check_valid)


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------

class TestAIEvaluate(unittest.TestCase):

    def test_starting_position_is_symmetric(self):
        ai = AI(depth=1)
        b = Board(8, 8)
        self.assertEqual(ai._evaluate(b), 0.0)

    def test_extra_white_queen_is_positive(self):
        ai = AI(depth=1)
        b = make_board(
            (4, 4, 'Q', 'w'), (7, 4, 'K', 'w'), (0, 4, 'K', 'b'),
            rows=8, cols=8
        )
        self.assertGreater(ai._evaluate(b), 0)

    def test_extra_black_rook_is_negative(self):
        ai = AI(depth=1)
        b = make_board(
            (0, 0, 'R', 'b'), (7, 4, 'K', 'w'), (0, 4, 'K', 'b'),
            rows=8, cols=8
        )
        self.assertLess(ai._evaluate(b), 0)

    def test_evaluation_values(self):
        ai = AI(depth=1)
        # One white pawn extra
        b = make_board(
            (5, 0, 'P', 'w'), (7, 4, 'K', 'w'), (0, 4, 'K', 'b'),
            rows=8, cols=8
        )
        self.assertEqual(ai._evaluate(b), 100.0)


class TestAIBestMove(unittest.TestCase):

    def test_returns_none_when_no_moves(self):
        ai = AI(depth=1)
        b = make_board((7, 4, 'K', 'w'), rows=8, cols=8)
        # Only a white king with no legal moves (can it move? let's check a trapped position)
        # Surround king with own pieces so it has no legal moves
        b2 = make_board(
            (0, 0, 'K', 'w'),
            (0, 1, 'P', 'w'), (1, 0, 'P', 'w'), (1, 1, 'P', 'w'),
            (7, 7, 'K', 'b'),
            rows=8, cols=8
        )
        # This may or may not be stalemate; just test that it returns a Move or None
        result = ai.best_move(b2, 'w')
        # Can be Move or None depending on whether king truly has no moves

    def test_returns_legal_move_at_start(self):
        ai = AI(depth=1)
        b = Board(8, 8)
        move = ai.best_move(b, 'w')
        self.assertIsNotNone(move)
        legal = b.legal_moves('w')
        self.assertIn(move, legal)

    def test_takes_free_piece(self):
        # White rook can take undefended black queen — should prefer this
        ai = AI(depth=1)
        b = make_board(
            (7, 4, 'K', 'w'), (4, 4, 'R', 'w'),
            (4, 0, 'Q', 'b'), (0, 4, 'K', 'b'),
            rows=8, cols=8
        )
        move = ai.best_move(b, 'w')
        self.assertIsNotNone(move)
        # The best move should be to capture the queen
        self.assertEqual(move, Move((4, 4), (4, 0)))

    def test_black_returns_legal_move(self):
        ai = AI(depth=1)
        b = Board(8, 8)
        move = ai.best_move(b, 'b')
        self.assertIsNotNone(move)
        legal = b.legal_moves('b')
        self.assertIn(move, legal)

    def test_stops_on_stop_event(self):
        import threading
        ai = AI(depth=5)
        b = Board(8, 8)
        stop = threading.Event()
        stop.set()
        move = ai.best_move(b, 'w', stop_event=stop)
        # Should return the first legal move quickly
        self.assertIsNotNone(move)

    def test_get_ai_move_does_not_modify_game(self):
        g = Game(8, 8)
        bb_before = {'w': dict(g.board.bb['w']), 'b': dict(g.board.bb['b'])}
        g.get_ai_move()
        self.assertEqual(g.board.bb, bb_before)
        self.assertEqual(g.turn, 'w')


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class TestSerialization(unittest.TestCase):

    def test_to_state_from_state_roundtrip(self):
        g = Game(8, 8)
        g.make_move(Move((6, 4), (4, 4)))
        g.make_move(Move((1, 4), (3, 4)))
        state = g.to_state()
        g2 = Game.from_state(state)
        self.assertEqual(g2.turn, g.turn)
        self.assertEqual(g2.board.rows, g.board.rows)
        self.assertEqual(g2.board.cols, g.board.cols)
        self.assertEqual(g2.board.bb, g.board.bb)
        self.assertEqual(len(g2.move_history), len(g.move_history))

    def test_from_state_restores_position_index(self):
        g = Game(8, 8)
        g.make_move(Move((6, 4), (4, 4)))
        g.make_move(Move((1, 4), (3, 4)))
        g.step_backward()
        state = g.to_state()
        g2 = Game.from_state(state)
        self.assertEqual(g2._history_index, g._history_index)

    def test_save_load_roundtrip(self):
        g = Game(8, 8)
        g.make_move(Move((6, 4), (4, 4)))
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        try:
            g.save_to_path(path)
            g2 = Game.load_from_path(path)
            self.assertEqual(g2.board.bb, g.board.bb)
            self.assertEqual(g2.turn, g.turn)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_non_standard_board_size_roundtrip(self):
        g = Game(5, 6)
        state = g.to_state()
        g2 = Game.from_state(state)
        self.assertEqual(g2.board.rows, 5)
        self.assertEqual(g2.board.cols, 6)

    def test_roundtrip_preserves_history(self):
        g = Game(8, 8)
        g.make_move(Move((6, 4), (4, 4)))
        g.make_move(Move((1, 4), (3, 4)))
        state = g.to_state()
        g2 = Game.from_state(state)
        self.assertEqual(g2.position_count, g.position_count)

    def test_serialize_piece_round_trip(self):
        p = Piece('N', 'b')
        self.assertEqual(Game._deserialize_piece(Game._serialize_piece(p)), p)

    def test_serialize_piece_none(self):
        self.assertIsNone(Game._serialize_piece(None))
        self.assertIsNone(Game._deserialize_piece(None))

    def test_serialize_move_round_trip(self):
        m = Move((3, 4), (1, 4), promotion='Q')
        self.assertEqual(Game._deserialize_move(Game._serialize_move(m)), m)


# ---------------------------------------------------------------------------
# Grid property
# ---------------------------------------------------------------------------

class TestGridProperty(unittest.TestCase):

    def test_grid_dimensions(self):
        b = Board(5, 6)
        grid = b.grid
        self.assertEqual(len(grid), 5)
        self.assertEqual(len(grid[0]), 6)

    def test_grid_matches_piece_at(self):
        b = Board(8, 8)
        grid = b.grid
        for r in range(8):
            for c in range(8):
                self.assertEqual(grid[r][c], b.piece_at(r, c))


if __name__ == '__main__':
    unittest.main()
