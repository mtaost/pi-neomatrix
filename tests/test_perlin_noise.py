import unittest

from display_modes.perlinnoise import PerlinNoise
from mode_settings import PERLIN_NOISE_SETTINGS, normalize_settings


class FakeDriver:
    width = 16
    height = 16


class PerlinNoiseTests(unittest.TestCase):
    def test_initializes_and_renders_palette_colors(self):
        mode = PerlinNoise(FakeDriver())
        mode.render_frame()
        pixels = list(mode.image.getdata())
        palette = set(mode.palette_colors)
        self.assertEqual(mode.image.size, (16, 16))
        self.assertTrue(any(pixel not in palette for pixel in pixels))
        self.assertGreater(len(set(pixels)), 4)

    def test_premade_palettes_and_custom_palette(self):
        for palette in ("aurora", "ocean", "sunset", "ember", "neon"):
            mode = PerlinNoise(FakeDriver(), {"palette": palette})
            self.assertEqual(len(mode.palette_colors), 4)

        mode = PerlinNoise(FakeDriver(), {"palette": "custom", "custom_start_color": "#102030", "custom_mid_color": "#405060", "custom_end_color": "#708090"})
        self.assertEqual(mode.palette_colors, ((16, 32, 48), (64, 80, 96), (112, 128, 144)))

    def test_settings_are_validated(self):
        with self.assertRaises(ValueError):
            normalize_settings(PERLIN_NOISE_SETTINGS, {"palette": "not-a-palette"})
        with self.assertRaises(ValueError):
            normalize_settings(PERLIN_NOISE_SETTINGS, {"octaves": 6})

    def test_settings_update_changes_render_configuration(self):
        mode = PerlinNoise(FakeDriver())
        mode.update_settings({"scale": 0.3, "octaves": 5, "contrast": 1.5})
        self.assertEqual(mode.octaves, 5)
        self.assertEqual(mode.scale, 0.3)
        self.assertEqual(mode.contrast, 1.5)


if __name__ == "__main__":
    unittest.main()
