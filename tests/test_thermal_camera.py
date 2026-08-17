import math
import unittest

from display_modes.thermalcamera import PALETTES, ThermalCamera
from mode_settings import THERMAL_SETTINGS, normalize_settings


class FakeDriver:
    width = 16
    height = 16


class FakeMLX90640:
    serial_number = (1, 2, 3)

    def __init__(self, values=None, failures=0):
        self.values = values or [20.0 + index / 100 for index in range(768)]
        self.failures = failures
        self.refresh_rate = None
        self.calls = 0

    def getFrame(self, frame):
        self.calls += 1
        if self.failures:
            self.failures -= 1
            raise ValueError("too many retries")
        frame[:] = self.values


class ThermalCameraTests(unittest.TestCase):
    def test_renders_nonblack_frame_from_sensor_data(self):
        sensor = FakeMLX90640()
        mode = ThermalCamera(FakeDriver(), sensor=sensor)
        self.assertEqual(sensor.refresh_rate, 4)
        self.assertTrue(mode._read_frame())
        mode._render_frame()
        self.assertEqual(mode.image.size, (16, 16))
        self.assertGreater(len(set(mode.image.getdata())), 1)

    def test_retries_are_reported_and_not_a_busy_loop(self):
        sensor = FakeMLX90640(failures=1)
        mode = ThermalCamera(FakeDriver(), sensor=sensor)
        self.assertFalse(mode._read_frame())
        self.assertIn("too many retries", mode._last_read_error)
        self.assertTrue(mode._read_frame())
        self.assertIsNone(mode._last_read_error)

    def test_refresh_rate_and_fixed_range_update_live(self):
        sensor = FakeMLX90640()
        mode = ThermalCamera(FakeDriver(), {"refresh_rate": "2", "exposure_mode": "fixed", "min_temperature": 5, "max_temperature": 40}, sensor=sensor)
        self.assertEqual(sensor.refresh_rate, 2)
        self.assertEqual(mode._temperature_range, (5.0, 40.0))
        mode.update_settings({"refresh_rate": "8", "palette": "grayscale"})
        self.assertEqual(sensor.refresh_rate, 8)
        self.assertEqual(mode.palette, PALETTES["grayscale"])

    def test_legacy_autorange_setting_is_migrated(self):
        legacy_options = normalize_settings(THERMAL_SETTINGS, {"autorange": False})
        mode = ThermalCamera(FakeDriver(), legacy_options, sensor=FakeMLX90640())
        self.assertEqual(mode.exposure_mode, "fixed")

    def test_percentile_exposure_rejects_temperature_outliers(self):
        mode = ThermalCamera(FakeDriver(), {"exposure_mode": "percentile", "low_percentile": 10, "high_percentile": 90}, sensor=FakeMLX90640())
        mode.frame_buffer = list(range(768))
        mode._update_temperature_range()
        self.assertGreater(mode._temperature_range[0], 0)
        self.assertLess(mode._temperature_range[1], 767)

    def test_exposure_smoothing_blends_range_changes(self):
        mode = ThermalCamera(FakeDriver(), {"exposure_smoothing": 0.5}, sensor=FakeMLX90640())
        mode.frame_buffer = [20.0] * 768
        mode._update_temperature_range()
        mode.frame_buffer = [40.0] * 768
        mode._update_temperature_range()
        self.assertEqual(mode._temperature_range, (29.75, 30.25))

    def test_invalid_sensor_values_do_not_become_black_without_diagnostics(self):
        sensor = FakeMLX90640(values=[math.nan] * 768)
        mode = ThermalCamera(FakeDriver(), sensor=sensor)
        self.assertFalse(mode._read_frame())
        self.assertIn("no finite temperatures", mode._last_read_error)

    def test_fixed_temperature_range_is_ordered(self):
        with self.assertRaisesRegex(ValueError, "Maximum temperature"):
            ThermalCamera(FakeDriver(), {"exposure_mode": "fixed", "min_temperature": 30, "max_temperature": 20}, sensor=FakeMLX90640())

    def test_individual_invalid_pixel_is_rendered_black(self):
        sensor = FakeMLX90640()
        mode = ThermalCamera(FakeDriver(), sensor=sensor)
        mode.frame_buffer[0] = None
        self.assertEqual(mode._get_color(None), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
