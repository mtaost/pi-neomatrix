from collections import deque
import unittest

from display_modes.gameoflife import GameOfLife


class FakeDriver:
    width = 16
    height = 16


def state_with_live_cell(x, y):
    state = [[0 for _ in range(16)] for _ in range(16)]
    state[x][y] = 1
    return state


class GameOfLifeCycleDetectionTests(unittest.TestCase):
    def test_detects_exact_cycles_with_periods_one_through_four(self):
        for period in range(1, 5):
            with self.subTest(period=period):
                mode = GameOfLife(FakeDriver())
                states = [state_with_live_cell(index, 0) for index in range(period)]
                mode.state = states[0]
                mode._state_history = deque(
                    (mode._state_signature(),), maxlen=mode.MAX_CYCLE_PERIOD
                )

                for state in states[1:] + [states[0]]:
                    mode.state = state
                    detected_period = mode.detectCycle(None)

                self.assertEqual(detected_period, period)
                self.assertEqual(mode.cycle_period, period)


    def test_supports_fixed_and_gradient_alive_colors(self):
        mode = GameOfLife(FakeDriver(), {"alive_color_mode": "fixed", "alive_fixed_color": "#123456", "dead_color": "#102030"})
        self.assertEqual(mode._alive_color(0, 0), (18, 52, 86))
        self.assertEqual(mode.dead_color, (16, 32, 48))

        mode.update_settings({"alive_color_mode": "rainbow_gradient", "rainbow_gradient_speed": 0})
        self.assertNotEqual(mode._alive_color(0, 0), mode._alive_color(8, 8))


if __name__ == "__main__":
    unittest.main()
