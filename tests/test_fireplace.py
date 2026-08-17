import unittest

from display_modes.fireplace import Fireplace, PALETTES
from mode_settings import FIREPLACE_SETTINGS, normalize_settings


class FakeDriver:
    width = 16
    height = 16


class FireplaceTests(unittest.TestCase):
    def test_renders_flames_and_keeps_a_log_bed(self):
        mode = Fireplace(FakeDriver(), {"ember_density": 0})
        mode.step()
        pixels = list(mode.image.getdata())
        self.assertEqual(mode.image.size, (16, 16))
        self.assertGreater(len(set(pixels)), 5)
        self.assertEqual(mode.pixels[0, 15], mode.LOG_DARK)
        self.assertTrue(any(pixel in mode.palette for pixel in pixels))

    def test_supports_curated_and_custom_palettes(self):
        self.assertEqual(len(PALETTES), 5)
        for name in PALETTES:
            mode = Fireplace(FakeDriver(), {"palette": name})
            self.assertEqual(len(mode.palette), 4)

        mode = Fireplace(FakeDriver(), {"palette": "custom", "custom_shadow_color": "#102030", "custom_mid_color": "#405060", "custom_highlight_color": "#708090"})
        self.assertEqual(mode.palette, ((16, 32, 48), (64, 80, 96), (112, 128, 144)))

    def test_settings_are_validated(self):
        with self.assertRaises(ValueError):
            normalize_settings(FIREPLACE_SETTINGS, {"flame_height": 1.1})
        with self.assertRaises(ValueError):
            normalize_settings(FIREPLACE_SETTINGS, {"palette": "unknown"})

    def test_ember_density_can_be_updated_live(self):
        mode = Fireplace(FakeDriver())
        mode.update_settings({"ember_density": 100, "flicker": 0.2})
        self.assertEqual(mode.ember_density, 100)
        self.assertEqual(mode.flicker, 0.2)


if __name__ == "__main__":
    unittest.main()
