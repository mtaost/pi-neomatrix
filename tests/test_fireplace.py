import unittest

from display_modes.fireplace import Fireplace, PALETTES
from mode_settings import FIREPLACE_SETTINGS, normalize_settings


class FakeDriver:
    width = 16
    height = 16


class FireplaceTests(unittest.TestCase):
    def test_renders_flames_and_keeps_a_log_bed(self):
        mode = Fireplace(FakeDriver(), {"ember_density": 0})
        # The cellular simulation needs a few frames for heat to rise.
        for _ in range(12):
            mode.step()
        pixels = list(mode.image.getdata())
        self.assertEqual(mode.image.size, (16, 16))
        self.assertGreater(len(set(pixels)), 5)
        self.assertEqual(mode.pixels[0, 15], mode.LOG_DARK)
        self.assertTrue(any(pixel != (0, 0, 0) for pixel in pixels[:14 * 16]))

    def test_heat_rises_from_bottom_without_perlin_phase(self):
        mode = Fireplace(FakeDriver(), {"ember_density": 0})
        self.assertEqual(len(mode.heat), 14)
        self.assertTrue(all(value == 0 for row in mode.heat for value in row))
        mode.step()
        self.assertTrue(any(value > 0 for value in mode.heat[-1]))
        self.assertFalse(hasattr(mode, "phase"))

        for _ in range(8):
            mode.step()
        self.assertTrue(any(value > 0 for row in mode.heat[:-1] for value in row))

    def test_flame_edge_tapers_as_heat_rises(self):
        mode = Fireplace(FakeDriver(), {"ember_density": 0})
        mode.heat[1] = [0.22] * mode.width
        mode._draw_flames()

        self.assertNotEqual(mode.pixels[7, 1], (0, 0, 0))
        self.assertEqual(mode.pixels[0, 1], (0, 0, 0))

    def test_peak_is_substantially_taller_than_the_sides(self):
        mode = Fireplace(FakeDriver(), {"ember_density": 0})
        mode.heat[9] = [0.8] * mode.width
        mode._draw_flames()

        self.assertNotEqual(mode.pixels[7, 9], (0, 0, 0))
        self.assertEqual(mode.pixels[0, 9], (0, 0, 0))

    def test_extended_flame_height_reduces_but_bounds_cooling(self):
        normal = Fireplace(FakeDriver(), {"flame_height": 1.0})
        extended = Fireplace(FakeDriver(), {"flame_height": 1.3})

        self.assertLess(extended._cooling_rate(), normal._cooling_rate())
        self.assertGreaterEqual(extended._cooling_rate(), 0.025)

    def test_supports_curated_and_custom_palettes(self):
        self.assertEqual(len(PALETTES), 5)
        for name in PALETTES:
            mode = Fireplace(FakeDriver(), {"palette": name})
            self.assertEqual(len(mode.palette), 4)

        mode = Fireplace(FakeDriver(), {"palette": "custom", "custom_shadow_color": "#102030", "custom_mid_color": "#405060", "custom_highlight_color": "#708090"})
        self.assertEqual(mode.palette, ((16, 32, 48), (64, 80, 96), (112, 128, 144)))

    def test_settings_are_validated(self):
        with self.assertRaises(ValueError):
            normalize_settings(FIREPLACE_SETTINGS, {"flame_height": 1.31})
        with self.assertRaises(ValueError):
            normalize_settings(FIREPLACE_SETTINGS, {"palette": "unknown"})

    def test_ember_density_can_be_updated_live(self):
        mode = Fireplace(FakeDriver())
        mode.update_settings({"ember_density": 100, "flicker": 0.2})
        self.assertEqual(mode.ember_density, 100)
        self.assertEqual(mode.flicker, 0.2)


if __name__ == "__main__":
    unittest.main()
