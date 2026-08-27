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

    def test_pixel_rain_can_vary_drop_speeds(self):
        mode = PixelRain(FakeDriver(), {"variable_drop_speed": True})
        mode._spawn_drop(0)
        mode._spawn_drop(1)
        self.assertNotEqual(mode.drops[0]["speed_factor"], mode.drops[1]["speed_factor"])

        mode.update_settings({"variable_drop_speed": False})
        self.assertTrue(all(drop["speed_factor"] == 1.0 for drop in mode.drops))
        mode._spawn_drop(2)
        self.assertEqual(mode.drops[-1]["speed_factor"], 1.0)

    def test_pixel_rain_accumulates_antialiased_trail_samples(self):
        mode = PixelRain(FakeDriver())
        mode._blend_pixel(0, 0, (100, 100, 100), 0.5)
        mode._blend_pixel(0, 0, (100, 100, 100), 0.5)
        self.assertEqual(mode.pixels[0, 0], (100, 100, 100))

    def test_pixel_rain_expands_light_density_range(self):
        self.assertAlmostEqual(PixelRain._density_behavior_fraction(0), 0.0)
        self.assertAlmostEqual(PixelRain._density_behavior_fraction(100), 0.02)
        self.assertAlmostEqual(PixelRain._density_behavior_fraction(500), 0.1)
        self.assertAlmostEqual(PixelRain._density_behavior_fraction(1000), 1.0)

    def test_pixel_rain_supports_twilight_palette(self):
        mode = PixelRain(FakeDriver(), {"palette": "twilight"})
        self.assertEqual(mode._spawn_color(0, 0), (18, 0, 48))
        self.assertEqual(mode._spawn_color(0, 15), (70, 155, 255))

    def test_pixel_rain_varies_new_trail_lengths(self):
        mode = PixelRain(FakeDriver(), {"trail_length_variance": 1.0, "drop_brightness_variance": 1.0})
        mode._random.seed(1)
        for x in range(8):
            mode._spawn_drop(x)
        lengths = {drop["trail_length"] for drop in mode.drops}
        self.assertGreater(len(lengths), 1)
        self.assertTrue(all(1 <= length <= len(mode.trail_brightness) for length in lengths))
        brightness = {drop["brightness_factor"] for drop in mode.drops}
        self.assertGreater(len(brightness), 1)
        self.assertTrue(all(0.5 <= value <= 1.5 for value in brightness))

        mode.update_settings({"trail_length_variance": 0.0, "drop_brightness_variance": 0.0})
        mode._spawn_drop(8)
        self.assertEqual(mode.drops[-1]["trail_length"], mode.base_trail_length)
        self.assertEqual(mode.drops[-1]["brightness_factor"], 1.0)

    def test_pixel_stars_initializes(self):
        mode = PixelStars(FakeDriver())
        self.assertEqual(mode.image.size, (16, 16))

    def test_pixel_stars_supports_fixed_and_gradient_colors(self):
        mode = PixelStars(FakeDriver(), {"star_color_mode": "fixed", "star_fixed_color": "#123456"})
        self.assertEqual(mode._spawn_color(0, 0), (18, 52, 86))

        mode.update_settings({"star_color_mode": "rainbow_gradient", "rainbow_gradient_speed": 0})
        self.assertNotEqual(mode._spawn_color(0, 0), mode._spawn_color(8, 8))


if __name__ == "__main__":
    unittest.main()
