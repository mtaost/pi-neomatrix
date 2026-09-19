import unittest

from display_modes.cityscape import Cityscape
from mode_settings import CITYSCAPE_SETTINGS, normalize_settings
from modes import build_mode_registry


class FakeDriver:
    width = 16
    height = 16


class CityscapeTests(unittest.TestCase):
    @staticmethod
    def frame_pixels(mode):
        return [mode.pixels[x, y] for y in range(mode.height) for x in range(mode.width)]

    def test_registry_exposes_cityscape_and_its_controls(self):
        spec = build_mode_registry()["cityscape"]
        self.assertEqual(spec.name, "Scrolling Cityscape")
        self.assertEqual(spec.settings_schema, CITYSCAPE_SETTINGS)

    def test_renders_a_daytime_city_with_a_scrollable_world(self):
        mode = Cityscape(FakeDriver(), {"sky_mode": "day", "scroll_speed": 1})
        mode.step(0)
        first_frame = self.frame_pixels(mode)
        self.assertEqual(mode.pixels[0, 0], mode.SKIES["day"][0])
        self.assertGreater(len(set(first_frame)), 4)

        mode.step(1)
        self.assertEqual(mode.scroll_offset, 1.0)
        self.assertNotEqual(first_frame, self.frame_pixels(mode))

    def test_night_lights_windows_and_cycle_reaches_sunset(self):
        mode = Cityscape(FakeDriver(), {"sky_mode": "night", "window_density": 100})
        mode.step(0)
        self.assertIn((255, 179, 63), self.frame_pixels(mode))

        mode.update_settings({"sky_mode": "cycle", "cycle_duration": 20})
        mode.cycle_elapsed = 15
        top, bottom, nightness, sunsetness = mode._sky()
        self.assertNotEqual(top, mode.SKIES["day"][0])
        self.assertNotEqual(bottom, mode.SKIES["night"][1])
        self.assertGreater(sunsetness, 0.5)
        self.assertLess(nightness, 0.5)

    def test_settings_are_validated_and_can_be_updated_live(self):
        with self.assertRaises(ValueError):
            normalize_settings(CITYSCAPE_SETTINGS, {"sky_mode": "dawn"})
        with self.assertRaises(ValueError):
            normalize_settings(CITYSCAPE_SETTINGS, {"scroll_speed": 9})

        mode = Cityscape(FakeDriver())
        mode.update_settings({"scroll_speed": 3.4, "building_height": 0.8})
        self.assertEqual(mode.scroll_speed, 3.4)
        self.assertEqual(mode.building_height, 0.8)


if __name__ == "__main__":
    unittest.main()
