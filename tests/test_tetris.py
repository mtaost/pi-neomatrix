import random
import tempfile
import unittest
from pathlib import Path

from cold_clear import ColdClearBot, ColdClearBotDead, ColdClearMove, MOVE_CCW, MOVE_CW, MOVE_DROP
from display_modes.tetris_engine import FallingPiece, QUEUE_LOOKAHEAD, TetrisGame
from display_modes.tetrisplayer import GHOST_COLORS, TetrisPlayer


class TetrisRulesTests(unittest.TestCase):
    def test_replays_a_sonic_drop_and_locks_the_advertised_cells(self):
        game = TetrisGame(random.Random(1))
        game.active = FallingPiece("I")
        move = ColdClearMove(False, ((3, 0), (4, 0), (5, 0), (6, 0)), (MOVE_DROP,))
        game.begin_bot_move(move)
        while not game.advance_animation():
            pass
        self.assertEqual([game.board[0][x] for x in range(3, 7)], ["I"] * 4)
        self.assertIsNone(game.active)

    def test_hard_drop_previews_the_projected_landing_before_locking(self):
        game = TetrisGame(random.Random(10))
        game.active = FallingPiece("I")
        move = ColdClearMove(False, ((3, 0), (4, 0), (5, 0), (6, 0)), (MOVE_DROP,))
        game.begin_bot_move(move)
        self.assertFalse(game.advance_animation())
        self.assertTrue(game.hard_drop_preview)
        self.assertEqual(frozenset(game.ghost_cells()), frozenset(move.cells))
        self.assertEqual(game.active.y, 19)
        self.assertTrue(game.advance_animation())
        self.assertIsNone(game.active)

    def test_replays_an_implicit_zero_g_drop_when_the_path_is_empty(self):
        game = TetrisGame(random.Random(8))
        game.active = FallingPiece("T")
        move = ColdClearMove(False, ((3, 0), (4, 0), (5, 0), (4, 1)), ())
        game.begin_bot_move(move)
        while not game.advance_animation():
            pass
        self.assertEqual(game.board[0][3:6], ["T", "T", "T"])
        self.assertEqual(game.board[1][4], "T")

    def test_replays_rotations_after_a_sonic_drop(self):
        game = TetrisGame(random.Random(9))
        game.active = FallingPiece("T")
        move = ColdClearMove(
            False,
            ((3, 0), (4, 0), (5, 0), (4, 1)),
            (MOVE_CW, MOVE_DROP, MOVE_CCW),
        )
        game.begin_bot_move(move)
        while not game.advance_animation():
            pass
        self.assertEqual(game.board[0][3:6], ["T", "T", "T"])
        self.assertEqual(game.board[1][4], "T")

    def test_rotation_changes_orientation_with_srs_geometry(self):
        game = TetrisGame(random.Random(2))
        game.active = FallingPiece("T", x=4, y=10, rotation="W")
        self.assertTrue(game._rotate(True))
        self.assertEqual(game.active.rotation, "N")
        self.assertTrue(all(0 <= x < 10 for x, _ in game.active.cells()))

    def test_spawn_uses_row_twenty_when_row_nineteen_is_blocked(self):
        game = TetrisGame(random.Random(6))
        game.board[19][3] = "Z"
        game.queue.clear()
        game.queue.append("T")
        self.assertTrue(game.start_turn())
        self.assertEqual(game.active.y, 20)

    def test_empty_hold_replenishes_the_bot_queue(self):
        game = TetrisGame(random.Random(7))
        added = []
        self.assertEqual(len(game.initial_queue), QUEUE_LOOKAHEAD + 1)
        self.assertTrue(game.start_turn(added.append))
        self.assertEqual(added, [])
        held_piece = game.active.kind
        next_piece = game.queue[0]
        move = ColdClearMove(True, FallingPiece(next_piece).cells(), ())
        game.begin_bot_move(move, added.append)
        self.assertEqual(game.hold_piece, held_piece)
        self.assertEqual(game.active.kind, next_piece)
        self.assertEqual(len(game.queue), QUEUE_LOOKAHEAD)
        self.assertEqual(len(added), 1)

    def test_garbage_pushes_the_stack_and_uses_grey_cells(self):
        game = TetrisGame(random.Random(3))
        game.board[0][0] = "T"
        game.garbage_hole = 4
        game.locks_since_garbage = 1
        self.assertTrue(game.apply_pending_garbage(True, 1, 0))
        self.assertEqual(game.board[0][4], None)
        self.assertEqual({cell for cell in game.board[0] if cell}, {"G"})
        self.assertEqual(game.board[1][0], "T")

    def test_garbage_event_can_add_multiple_rows(self):
        game = TetrisGame(random.Random(11))
        game.board[0][0] = "T"
        game.garbage_hole = 4
        game.locks_since_garbage = 1
        self.assertTrue(game.apply_pending_garbage(True, 1, 0, lines=3))
        self.assertEqual(game.board[3][0], "T")
        for row in game.board[:3]:
            self.assertEqual(row[4], None)
            self.assertEqual({cell for cell in row if cell}, {"G"})

    def test_garbage_messiness_controls_hole_changes(self):
        game = TetrisGame(random.Random(4))
        game.garbage_hole = 3
        game.locks_since_garbage = 1
        game.apply_pending_garbage(True, 1, 0)
        self.assertEqual(game.garbage_hole, 3)
        game.locks_since_garbage = 1
        game.apply_pending_garbage(True, 1, 1)
        self.assertNotEqual(game.garbage_hole, 3)

    def test_garbage_overflow_ends_the_round(self):
        game = TetrisGame(random.Random(5))
        game.board[-1][0] = "Z"
        game.locks_since_garbage = 1
        game.apply_pending_garbage(True, 1, 0)
        self.assertTrue(game.game_over)


class ColdClearAdapterTests(unittest.TestCase):
    def test_missing_library_reports_build_instruction(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "libcold_clear.so"
            with self.assertRaisesRegex(RuntimeError, "build-cold-clear"):
                ColdClearBot(("I",), library_path=missing)


class _Driver:
    width = 16
    height = 16


class _Bot:
    instances = []
    raise_dead = False

    def __init__(self, pieces, strategy):
        self.pieces = tuple(pieces)
        self.strategy = strategy
        self.closed = False
        self.added = []
        self.requests = 0
        _Bot.instances.append(self)

    def add_next_piece(self, piece):
        self.added.append(piece)

    def request_move(self):
        self.requests += 1

    def poll_move(self):
        if _Bot.raise_dead:
            raise ColdClearBotDead("no surviving move")
        return None

    def reset(self, *args):
        pass

    def close(self):
        self.closed = True


class TetrisPlayerSettingsTests(unittest.TestCase):
    def setUp(self):
        _Bot.instances = []
        _Bot.raise_dead = False

    def test_speed_and_garbage_update_live_while_strategy_restarts(self):
        player = TetrisPlayer(_Driver(), bot_factory=_Bot)
        original_bot = player.bot
        player.update_settings({"animation_speed": 0.13, "simulated_garbage": True, "garbage_frequency": 3, "garbage_lines": 4})
        self.assertIs(player.bot, original_bot)
        self.assertEqual(player.settings["animation_speed"], 0.13)
        self.assertTrue(player.settings["simulated_garbage"])
        self.assertEqual(player.settings["garbage_frequency"], 3)
        self.assertEqual(player.settings["garbage_lines"], 4)
        player.update_settings({"strategy": "fast"})
        self.assertTrue(original_bot.closed)
        self.assertEqual(player.bot.strategy, "fast")
        player.cleanup()

    def test_garbage_frequency_slider_runs_from_rare_to_frequent(self):
        self.assertEqual(TetrisPlayer._garbage_interval(1), 10)
        self.assertEqual(TetrisPlayer._garbage_interval(10), 1)

    def test_bot_dead_ends_the_round_without_crashing_the_mode(self):
        player = TetrisPlayer(_Driver(), bot_factory=_Bot)
        _Bot.raise_dead = True
        player._advance()
        self.assertEqual(player.phase, "game_over")
        player.cleanup()

    def test_draws_a_dim_ghost_at_the_projected_landing(self):
        player = TetrisPlayer(_Driver(), bot_factory=_Bot)
        player.game.active = FallingPiece("T")
        player._draw()
        for x, y in player.game.ghost_cells():
            self.assertEqual(player.pixels[x, 15 - y], GHOST_COLORS["T"])
        player.cleanup()


if __name__ == "__main__":
    unittest.main()
