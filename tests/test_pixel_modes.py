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

    def test_pixel_stars_initializes(self):
        mode = PixelStars(FakeDriver())
        self.assertEqual(mode.image.size, (16, 16))


if __name__ == "__main__":
    unittest.main()
