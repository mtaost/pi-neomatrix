"""MLX90640 thermal camera display mode."""

import logging
import math
import threading

from PIL import Image

from display_modes import module
from mode_settings import THERMAL_SETTINGS, hex_to_rgb, normalize_settings


logger = logging.getLogger(__name__)


PALETTES = {
    "rainbow": ((0, 0, 128), (0, 100, 255), (0, 220, 180), (255, 230, 0), (255, 30, 0)),
    "ironbow": ((0, 0, 0), (55, 0, 90), (190, 0, 25), (255, 100, 0), (255, 230, 60), (255, 255, 255)),
    "amber": ((10, 0, 0), (120, 25, 0), (255, 135, 0), (255, 235, 150)),
    "grayscale": ((0, 0, 0), (255, 255, 255)),
    "cool": ((0, 0, 30), (0, 60, 180), (0, 210, 255), (220, 255, 255)),
}


class ThermalCamera(module.Module):
    """Read 32x24 MLX90640 frames and resize them to the matrix."""

    SENSOR_WIDTH = 32
    SENSOR_HEIGHT = 24
    FRAME_SIZE = SENSOR_WIDTH * SENSOR_HEIGHT
    I2C_FREQUENCY = 800000
    RETRY_DELAY = 0.25

    def __init__(self, driver, options=None, sensor=None, i2c=None, thermal_service=None):
        super().__init__(driver)
        options = dict(options or {})
        thermal_service = options.pop("thermal_service", thermal_service)
        self.thermal_service = thermal_service
        self._sensor_lock = threading.Lock()
        self._owns_i2c = False
        self.frame_buffer = [0.0] * self.FRAME_SIZE
        self.thermal_image = Image.new("RGB", (self.SENSOR_WIDTH, self.SENSOR_HEIGHT), "black")
        self.thermal_pixels = self.thermal_image.load()
        self._refresh_rate_enum = None
        self._last_read_error = None
        self._exposure_frame = 0
        self._temperature_range = (20.0, 40.0)
        self._range_initialized = False

        self._last_frame_timestamp = None
        self.update_settings(options)
        self.mlx, self.i2c = self._initialize_sensor(sensor, i2c)
        self._apply_refresh_rate()

    def _initialize_sensor(self, sensor, i2c):
        if self.thermal_service is not None:
            logger.info("Using shared MLX90640 thermal service")
            return None, None
        if sensor is not None:
            logger.info("Using injected MLX90640 sensor")
            return sensor, i2c

        import adafruit_mlx90640
        import board
        import busio

        if i2c is None:
            i2c = busio.I2C(board.SCL, board.SDA, frequency=self.I2C_FREQUENCY)
            self._owns_i2c = True
        sensor = adafruit_mlx90640.MLX90640(i2c)
        self._refresh_rate_enum = adafruit_mlx90640.RefreshRate
        logger.info("MLX90640 detected on I2C; serial=%s", [hex(value) for value in sensor.serial_number])
        return sensor, i2c

    def _apply_refresh_rate(self):
        if self.thermal_service is not None:
            self.thermal_service.set_refresh_rate(self.settings["refresh_rate"])
            return
        if not hasattr(self.mlx, "refresh_rate"):
            return
        rate = int(self.settings["refresh_rate"])
        if self._refresh_rate_enum is not None:
            rate = getattr(self._refresh_rate_enum, f"REFRESH_{rate}_HZ")
        with self._sensor_lock:
            self.mlx.refresh_rate = rate
        logger.info("MLX90640 refresh rate set to %s Hz", self.settings["refresh_rate"])

    def update_settings(self, values=None):
        requested = values if isinstance(values, dict) else {}
        previous_mode = getattr(self, "exposure_mode", None)
        legacy_autorange = previous_mode is None and requested.get("autorange") is False and requested.get("exposure_mode", "auto") == "auto"
        previous_rate = getattr(self, "settings", {}).get("refresh_rate")
        self.settings = normalize_settings(THERMAL_SETTINGS, values, getattr(self, "settings", None))
        if legacy_autorange:
            self.settings["exposure_mode"] = "auto" if self.settings["autorange"] else "fixed"
        self.exposure_mode = self.settings["exposure_mode"]
        self.autorange = self.exposure_mode != "fixed"
        self.exposure_smoothing = self.settings["exposure_smoothing"]
        self.palette_name = self.settings["palette"]
        if self.palette_name == "custom":
            colors = (
                self.settings["custom_cold_color"],
                self.settings["custom_mid_color"],
                self.settings["custom_hot_color"],
            )
            self.palette = tuple(hex_to_rgb(value) for value in colors)
        else:
            self.palette = PALETTES[self.palette_name]
        self._temperature_range = (self.settings["min_temperature"], self.settings["max_temperature"])
        if self._temperature_range[1] <= self._temperature_range[0]:
            raise ValueError("Maximum temperature must be greater than minimum temperature.")
        if self.settings["high_percentile"] <= self.settings["low_percentile"]:
            raise ValueError("High percentile must be greater than low percentile.")
        if previous_mode != self.exposure_mode:
            self._range_initialized = False
        if self.exposure_mode == "fixed":
            self._range_initialized = True
        if hasattr(self, "mlx") and previous_rate != self.settings["refresh_rate"]:
            self._apply_refresh_rate()
        return dict(self.settings)

    @staticmethod
    def _interpolate(start, end, amount):
        return tuple(round(first + (last - first) * amount) for first, last in zip(start, end))

    def _get_color(self, temperature):
        """Map a temperature to the current palette without throwing on bad data."""
        try:
            temperature = float(temperature)
        except (TypeError, ValueError):
            return (0, 0, 0)
        if not math.isfinite(temperature):
            return (0, 0, 0)
        low, high = self._temperature_range
        if high <= low:
            return self.palette[-1]
        normalized = min(1.0, max(0.0, (temperature - low) / (high - low)))
        position = normalized * (len(self.palette) - 1)
        index = min(len(self.palette) - 2, int(position))
        return self._interpolate(self.palette[index], self.palette[index + 1], position - index)

    def _valid_temperatures(self):
        temperatures = []
        for value in self.frame_buffer:
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(value):
                temperatures.append(value)
        return temperatures

    def _update_temperature_range(self):
        if self.exposure_mode == "fixed":
            return
        temperatures = self._valid_temperatures()
        if not temperatures:
            raise ValueError("MLX90640 returned no finite temperatures")
        temperatures.sort()
        if self.exposure_mode == "percentile":
            low = self._percentile(temperatures, self.settings["low_percentile"])
            high = self._percentile(temperatures, self.settings["high_percentile"])
        else:
            low, high = min(temperatures), max(temperatures)
        if high - low < 0.5:
            midpoint = (low + high) / 2.0
            low, high = midpoint - 0.25, midpoint + 0.25
        if self._range_initialized and self.exposure_smoothing:
            old_low, old_high = self._temperature_range
            smoothing = self.exposure_smoothing
            low = old_low * smoothing + low * (1.0 - smoothing)
            high = old_high * smoothing + high * (1.0 - smoothing)
        self._temperature_range = (low, high)
        self._range_initialized = True

    @staticmethod
    def _percentile(values, percentile):
        position = (len(values) - 1) * percentile / 100.0
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return values[lower]
        amount = position - lower
        return values[lower] + (values[upper] - values[lower]) * amount

    def _read_frame(self):
        try:
            if self.thermal_service is not None:
                latest = self.thermal_service.get_latest_frame()
                if latest is None:
                    raise ValueError("MLX90640 has not produced a frame yet")
                frame, timestamp = latest
                self.frame_buffer = list(frame)
                self._last_frame_timestamp = timestamp
            else:
                with self._sensor_lock:
                    self.mlx.getFrame(self.frame_buffer)
            if len(self.frame_buffer) != self.FRAME_SIZE:
                raise ValueError(f"MLX90640 returned {len(self.frame_buffer)} values; expected {self.FRAME_SIZE}")
            if not self._valid_temperatures():
                raise ValueError("MLX90640 returned no finite temperatures")
            if self._exposure_frame == 0:
                self._update_temperature_range()
            self._exposure_frame = (self._exposure_frame + 1) % 5
        except Exception as error:
            message = f"{type(error).__name__}: {error}"
            if message != self._last_read_error:
                logger.warning("MLX90640 frame read failed; retrying: %s", message)
                self._last_read_error = message
            return False

        if self._last_read_error is not None:
            logger.info("MLX90640 frame acquisition recovered")
            self._last_read_error = None
        return True

    def _render_frame(self):
        for y in range(self.SENSOR_HEIGHT):
            for x in range(self.SENSOR_WIDTH):
                self.thermal_pixels[x, y] = self._get_color(self.frame_buffer[y * self.SENSOR_WIDTH + x])
        self.image = self.thermal_image.resize((self.width, self.height), Image.Resampling.BILINEAR)
        self.pixels = self.image.load()

    def run(self):
        while not self.should_stop():
            if not self._read_frame():
                if not self.wait(self.RETRY_DELAY):
                    break
                continue
            self._render_frame()
            self.display()

    def cleanup(self):
        if self._owns_i2c and self.i2c is not None and hasattr(self.i2c, "deinit"):
            try:
                self.i2c.deinit()
            except Exception:
                logger.warning("Unable to release MLX90640 I2C bus", exc_info=True)
