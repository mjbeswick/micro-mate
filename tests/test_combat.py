"""Unit tests for dice combat mode."""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from micromate.engine import AI, Board, Game, GameSnapshot, Move, Piece, _empty_bb

# Suppress pygame display / audio output before importing run_game
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

from run_game import _combat_outcome, _attempt_capture_with_dice


def _make_game_with_pieces(*pieces, rows=8, cols=8, turn='w'):
    """Return a minimal Game with only the given pieces on the board."""
    g = Game.__new__(Game)
    b = Board.__new__(Board)
    b.rows = rows
    b.cols = cols
    b.bb = _empty_bb()
    for r, c, kind, color in pieces:
        b._set_piece(r, c, Piece(kind, color))
    g.board = b
    g.turn = turn
    g.move_history = []
    g._history = [GameSnapshot(bb={'w': dict(b.bb['w']), 'b': dict(b.bb['b'])}, turn=turn)]
    g._history_index = 0
    g.ai_depth = 1
    g.ai = AI(depth=1)
    g._king_check_valid = False
    g._king_check_sq = None
    return g


# ---------------------------------------------------------------------------
# _combat_outcome
# ---------------------------------------------------------------------------

class TestCombatOutcome(unittest.TestCase):

    # --- attacker_wins ---

    def test_attacker_wins_when_atk_higher(self):
        self.assertEqual(_combat_outcome(6, 1), 'attacker_wins')

    def test_attacker_wins_with_minimal_lead(self):
        self.assertEqual(_combat_outcome(2, 1), 'attacker_wins')

    def test_attacker_wins_five_vs_four(self):
        self.assertEqual(_combat_outcome(5, 4), 'attacker_wins')

    # --- defender_wins ---

    def test_defender_wins_when_def_higher(self):
        self.assertEqual(_combat_outcome(1, 6), 'defender_wins')

    def test_defender_wins_with_minimal_lead(self):
        self.assertEqual(_combat_outcome(1, 2), 'defender_wins')

    def test_defender_wins_three_vs_four(self):
        self.assertEqual(_combat_outcome(3, 4), 'defender_wins')

    # --- blocked ---

    def test_blocked_on_equal_rolls(self):
        for v in range(1, 7):
            with self.subTest(v=v):
                self.assertEqual(_combat_outcome(v, v), 'blocked')

    # --- exhaustive check: no illegal outcomes ---

    def test_all_roll_combinations_produce_valid_outcome(self):
        valid = {'attacker_wins', 'defender_wins', 'blocked'}
        for a in range(1, 7):
            for d in range(1, 7):
                result = _combat_outcome(a, d)
                self.assertIn(result, valid, f"Invalid outcome for ({a},{d}): {result}")

    def test_higher_always_wins(self):
        for a in range(1, 7):
            for d in range(1, 7):
                outcome = _combat_outcome(a, d)
                if a > d:
                    self.assertEqual(outcome, 'attacker_wins', f"({a},{d})")
                elif d > a:
                    self.assertEqual(outcome, 'defender_wins', f"({a},{d})")
                else:
                    self.assertEqual(outcome, 'blocked', f"({a},{d})")


# ---------------------------------------------------------------------------
# _attempt_capture_with_dice (screen=None, no modal shown)
# ---------------------------------------------------------------------------

class TestAttemptCaptureWithDice(unittest.TestCase):

    def setUp(self):
        self.g = _make_game_with_pieces(
            (4, 4, 'R', 'w'), (4, 6, 'P', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
        )
        self.atk = Piece('R', 'w')
        self.def_ = Piece('P', 'b')
        self.move = Move((4, 4), (4, 6))

    def _call(self, atk_roll, def_roll):
        with patch('run_game.random.randint', side_effect=[atk_roll, def_roll]):
            return _attempt_capture_with_dice(
                self.g, self.move, self.atk, self.def_, None, 0
            )

    # --- attacker_wins ---

    def test_returns_true_on_attacker_wins(self):
        result = self._call(5, 3)
        self.assertTrue(result)

    def test_board_unchanged_on_attacker_wins(self):
        # Caller is responsible for executing the move after True
        self._call(5, 3)
        self.assertEqual(self.g.board.piece_at(4, 4), Piece('R', 'w'))
        self.assertEqual(self.g.board.piece_at(4, 6), Piece('P', 'b'))

    def test_turn_unchanged_on_attacker_wins(self):
        self._call(5, 3)
        self.assertEqual(self.g.turn, 'w')

    # --- defender_wins ---

    def test_returns_false_on_defender_wins(self):
        result = self._call(2, 5)
        self.assertFalse(result)

    def test_attacker_removed_on_defender_wins(self):
        self._call(2, 5)
        self.assertIsNone(self.g.board.piece_at(4, 4))

    def test_defender_survives_on_defender_wins(self):
        self._call(2, 5)
        self.assertEqual(self.g.board.piece_at(4, 6), Piece('P', 'b'))

    def test_turn_advances_on_defender_wins(self):
        self._call(2, 5)
        self.assertEqual(self.g.turn, 'b')

    def test_history_recorded_on_defender_wins(self):
        before = self.g.position_count
        self._call(2, 5)
        self.assertEqual(self.g.position_count, before + 1)

    # --- blocked ---

    def test_returns_false_on_blocked(self):
        result = self._call(4, 4)
        self.assertFalse(result)

    def test_attacker_survives_on_blocked(self):
        self._call(4, 4)
        self.assertEqual(self.g.board.piece_at(4, 4), Piece('R', 'w'))

    def test_defender_survives_on_blocked(self):
        self._call(4, 4)
        self.assertEqual(self.g.board.piece_at(4, 6), Piece('P', 'b'))

    def test_turn_advances_on_blocked(self):
        self._call(4, 4)
        self.assertEqual(self.g.turn, 'b')

    def test_history_recorded_on_blocked(self):
        before = self.g.position_count
        self._call(4, 4)
        self.assertEqual(self.g.position_count, before + 1)


# ---------------------------------------------------------------------------
# Turn advancement invariant across all outcomes
# ---------------------------------------------------------------------------

class TestTurnAlwaysAdvances(unittest.TestCase):
    """After _attempt_capture_with_dice completes, the turn must have advanced
    for defender_wins and blocked outcomes (the turn is consumed). For
    attacker_wins the caller makes the move, so the function itself must not
    advance the turn."""

    def _make_setup(self):
        g = _make_game_with_pieces(
            (4, 4, 'R', 'w'), (4, 6, 'P', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
        )
        return g

    def test_defender_wins_advances_to_black(self):
        g = self._make_setup()
        with patch('run_game.random.randint', side_effect=[1, 6]):
            _attempt_capture_with_dice(g, Move((4,4),(4,6)), Piece('R','w'), Piece('P','b'), None, 0)
        self.assertEqual(g.turn, 'b')

    def test_blocked_advances_to_black(self):
        g = self._make_setup()
        with patch('run_game.random.randint', side_effect=[3, 3]):
            _attempt_capture_with_dice(g, Move((4,4),(4,6)), Piece('R','w'), Piece('P','b'), None, 0)
        self.assertEqual(g.turn, 'b')

    def test_attacker_wins_does_not_advance_turn(self):
        g = self._make_setup()
        with patch('run_game.random.randint', side_effect=[6, 1]):
            _attempt_capture_with_dice(g, Move((4,4),(4,6)), Piece('R','w'), Piece('P','b'), None, 0)
        self.assertEqual(g.turn, 'w')


# ---------------------------------------------------------------------------
# Check detection after combat outcomes
# ---------------------------------------------------------------------------

class TestCheckAfterCombat(unittest.TestCase):

    def test_removing_attacker_clears_check_it_was_giving(self):
        """When an attacker that was giving check loses the dice roll, the check must clear."""
        g = _make_game_with_pieces(
            (7, 4, 'K', 'w'), (5, 4, 'R', 'b'), (0, 0, 'K', 'b'),
            turn='b'
        )
        self.assertTrue(g.board._is_in_check('w'))
        # Black rook tries to capture something but dice say black loses
        g.make_attacker_loss(Move((5, 4), (7, 4)))
        self.assertFalse(g.board._is_in_check('w'))

    def test_skip_turn_does_not_create_check(self):
        """A blocked combat must not leave either side in check when it wasn't before."""
        g = _make_game_with_pieces(
            (7, 4, 'K', 'w'), (4, 4, 'R', 'w'), (4, 6, 'P', 'b'), (0, 0, 'K', 'b'),
        )
        self.assertFalse(g.board._is_in_check('w'))
        self.assertFalse(g.board._is_in_check('b'))
        g.skip_turn(Move((4, 4), (4, 6)))
        self.assertFalse(g.board._is_in_check('w'))
        self.assertFalse(g.board._is_in_check('b'))

    def test_ai_can_move_after_combat_advances_turn(self):
        """After any dice outcome, if it's the AI's turn it must be able to find a move."""
        g = _make_game_with_pieces(
            (7, 4, 'K', 'w'), (4, 4, 'R', 'w'), (4, 6, 'P', 'b'),
            (1, 0, 'P', 'b'), (0, 0, 'K', 'b'),
        )
        # Simulate: human's attacker loses → turn passes to AI (black)
        g.make_attacker_loss(Move((4, 4), (4, 6)))
        self.assertEqual(g.turn, 'b')
        move = g.get_ai_move()
        self.assertIsNotNone(move)
        legal = g.board.legal_moves('b')
        self.assertIn(move, legal)

    def test_ai_can_move_after_blocked_advance(self):
        """After a blocked attack advances the turn to AI, the AI must find a legal move."""
        g = _make_game_with_pieces(
            (7, 4, 'K', 'w'), (4, 4, 'R', 'w'), (4, 6, 'P', 'b'),
            (1, 0, 'P', 'b'), (0, 0, 'K', 'b'),
        )
        g.skip_turn(Move((4, 4), (4, 6)))
        self.assertEqual(g.turn, 'b')
        move = g.get_ai_move()
        self.assertIsNotNone(move)

    def test_combat_does_not_strand_king_in_check(self):
        """skip_turn and make_attacker_loss must never leave either king in an
        illegal state that the engine cannot recover from."""
        g = _make_game_with_pieces(
            (7, 4, 'K', 'w'), (4, 4, 'R', 'w'), (4, 6, 'N', 'b'),
            (0, 4, 'K', 'b'),
        )
        # Blocked: nothing changes, AI's turn
        g.skip_turn(Move((4, 4), (4, 6)))
        # Verify that legal_moves() does not crash and returns sensible results
        legal = g.board.legal_moves(g.turn)
        self.assertIsInstance(legal, list)


# ---------------------------------------------------------------------------
# History coherence after combat moves
# ---------------------------------------------------------------------------

class TestCombatHistory(unittest.TestCase):

    def test_history_grows_after_attacker_loss(self):
        g = _make_game_with_pieces(
            (4, 4, 'R', 'w'), (4, 6, 'P', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
        )
        before = g.position_count
        g.make_attacker_loss(Move((4, 4), (4, 6)))
        self.assertEqual(g.position_count, before + 1)

    def test_history_grows_after_skip_turn(self):
        g = _make_game_with_pieces(
            (4, 4, 'R', 'w'), (4, 6, 'P', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
        )
        before = g.position_count
        g.skip_turn(Move((4, 4), (4, 6)))
        self.assertEqual(g.position_count, before + 1)

    def test_step_back_after_attacker_loss_restores_piece(self):
        g = _make_game_with_pieces(
            (4, 4, 'R', 'w'), (4, 6, 'P', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
        )
        g.make_attacker_loss(Move((4, 4), (4, 6)))
        g.step_backward()
        # Rook should be restored
        self.assertEqual(g.board.piece_at(4, 4), Piece('R', 'w'))

    def test_step_back_after_skip_turn_restores_turn(self):
        g = _make_game_with_pieces(
            (4, 4, 'R', 'w'), (4, 6, 'P', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
        )
        g.skip_turn(Move((4, 4), (4, 6)))
        g.step_backward()
        self.assertEqual(g.turn, 'w')

    def test_new_move_after_combat_truncates_redo(self):
        g = _make_game_with_pieces(
            (4, 4, 'R', 'w'), (4, 6, 'P', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
        )
        g.skip_turn(Move((4, 4), (4, 6)))
        g.step_backward()
        # Make a real move from original position
        g.make_move(Move((7, 7), (6, 7)))  # move white king
        self.assertFalse(g.can_step_forward())

    def test_mixed_combat_and_normal_moves_navigable(self):
        g = _make_game_with_pieces(
            (4, 4, 'R', 'w'), (4, 6, 'P', 'b'),
            (7, 7, 'K', 'w'), (0, 0, 'K', 'b'),
        )
        # White skip → black normal move → white attacker loss
        g.skip_turn(Move((4, 4), (4, 6)))
        g.make_move(Move((0, 0), (1, 0)))   # black king moves
        g.make_attacker_loss(Move((4, 4), (4, 6)))

        # Step back to beginning
        while g.can_step_backward():
            g.step_backward()
        self.assertEqual(g._history_index, 0)
        self.assertEqual(g.turn, 'w')


# ---------------------------------------------------------------------------
# Dice outcome distribution (statistical sanity)
# ---------------------------------------------------------------------------

class TestCombatOutcomeDistribution(unittest.TestCase):
    """Check that _combat_outcome produces all three outcomes across the 36 roll combos."""

    def test_all_three_outcomes_reachable(self):
        outcomes = set()
        for a in range(1, 7):
            for d in range(1, 7):
                outcomes.add(_combat_outcome(a, d))
        self.assertEqual(outcomes, {'attacker_wins', 'defender_wins', 'blocked'})

    def test_blocked_only_on_equal_rolls(self):
        for a in range(1, 7):
            for d in range(1, 7):
                if _combat_outcome(a, d) == 'blocked':
                    self.assertEqual(a, d)

    def test_six_blocked_outcomes_out_of_36(self):
        blocked = sum(
            1 for a in range(1, 7) for d in range(1, 7)
            if _combat_outcome(a, d) == 'blocked'
        )
        self.assertEqual(blocked, 6)

    def test_attacker_defender_symmetric(self):
        atk_wins = sum(
            1 for a in range(1, 7) for d in range(1, 7)
            if _combat_outcome(a, d) == 'attacker_wins'
        )
        def_wins = sum(
            1 for a in range(1, 7) for d in range(1, 7)
            if _combat_outcome(a, d) == 'defender_wins'
        )
        self.assertEqual(atk_wins, def_wins)


if __name__ == '__main__':
    unittest.main()
