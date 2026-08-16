import unittest

from display_modes.pixelrain import PixelRain
from display_modes.pixelstars import PixelStars


class FakeDriver:
    width = 16
    height = 16


class PixelModeInitializationTests(unittest.TestCase):
    def test_pixel_rain_initializes(self):
        mode = PixelRain(FakeDriver())
        self.assertEqual(mode.image.size, (16, 16))

    def test_pixel_rain_supports_fixed_and_gradient_colors(self):
        mode = PixelRain(FakeDriver(), {"rain_color_mode": "fixed", "rain_fixed_color": "#123456"})
        self.assertEqual(mode._spawn_color(0), (18, 52, 86))

        mode.update_settings({"rain_color_mode": "rainbow_gradient", "rainbow_gradient_speed": 0})
        self.assertNotEqual(mode._spawn_color(0), mode._spawn_color(8))

    def test_pixel_stars_initializes(self):
        mode = PixelStars(FakeDriver())
        self.assertEqual(mode.image.size, (16, 16))


if __name__ == "__main__":
    unittest.main()
