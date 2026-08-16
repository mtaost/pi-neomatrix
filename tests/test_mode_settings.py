import unittest

from mode_settings import (
    FIREWORKS_SETTINGS,
    GAME_OF_LIFE_SETTINGS,
    PIXEL_RAIN_SETTINGS,
    PIXEL_STARS_SETTINGS,
    TETRIS_SETTINGS,
)


class SpeedSliderSettingsTests(unittest.TestCase):
    def test_wait_time_speed_sliders_are_inverted_for_the_ui(self):
        self.assertTrue(GAME_OF_LIFE_SETTINGS["iteration_delay"]["inverse"])
        self.assertTrue(PIXEL_RAIN_SETTINGS["frame_delay"]["inverse"])
        self.assertTrue(PIXEL_STARS_SETTINGS["frame_delay"]["inverse"])
        self.assertTrue(FIREWORKS_SETTINGS["frame_delay"]["inverse"])
        self.assertTrue(TETRIS_SETTINGS["animation_speed"]["inverse"])


if __name__ == "__main__":
    unittest.main()
