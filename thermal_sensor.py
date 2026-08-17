"""Shared background acquisition service for the MLX90640."""

import logging
import math
import threading
import time


logger = logging.getLogger(__name__)


class ThermalSensorService:
    WIDTH = 32
    HEIGHT = 24
    FRAME_SIZE = WIDTH * HEIGHT
    I2C_FREQUENCY = 800000

    def __init__(self, sensor=None, i2c=None, refresh_rate=4, on_frame=None, on_error=None):
        self._lock = threading.RLock()
        self._frame = None
        self._updated_at = None
        self._last_error = None
        self._on_frame = on_frame
        self._on_error = on_error
        self._stop_event = threading.Event()
        self._thread = None
        self._owns_i2c = False
        self._refresh_rate_enum = None
        self.sensor, self.i2c = self._initialize_sensor(sensor, i2c)
        self.set_refresh_rate(refresh_rate)

    def _initialize_sensor(self, sensor, i2c):
        if sensor is not None:
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

    def set_callbacks(self, on_frame=None, on_error=None):
        with self._lock:
            self._on_frame = on_frame
            self._on_error = on_error

    def set_refresh_rate(self, refresh_rate):
        try:
            refresh_rate = int(refresh_rate)
        except (TypeError, ValueError) as error:
            raise ValueError("Thermal refresh rate must be numeric.") from error
        if refresh_rate not in {2, 4, 8, 16, 32}:
            raise ValueError("Thermal refresh rate must be 2, 4, 8, 16, or 32 Hz.")
        value = refresh_rate
        if self._refresh_rate_enum is not None:
            value = getattr(self._refresh_rate_enum, f"REFRESH_{refresh_rate}_HZ")
        with self._lock:
            if hasattr(self.sensor, "refresh_rate"):
                self.sensor.refresh_rate = value
            self.refresh_rate = refresh_rate
        logger.info("MLX90640 refresh rate set to %s Hz", refresh_rate)

    def start(self):
        with self._lock:
            if self._thread is not None:
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, name="thermal-sensor", daemon=True)
            self._thread.start()
        logger.info("Starting thermal sensor service")

    def stop(self):
        self._stop_event.set()
        thread = self._thread
        if thread:
            thread.join(timeout=2)
        with self._lock:
            self._thread = None
        if self._owns_i2c and self.i2c is not None and hasattr(self.i2c, "deinit"):
            try:
                self.i2c.deinit()
            except Exception:
                logger.warning("Unable to release MLX90640 I2C bus", exc_info=True)
        logger.info("Thermal sensor service stopped")

    def get_latest_frame(self):
        with self._lock:
            if self._frame is None:
                return None
            return list(self._frame), self._updated_at

    def status(self):
        with self._lock:
            return {
                "available": self.sensor is not None,
                "updated_at": self._updated_at,
                "error": self._last_error,
                "refresh_rate": getattr(self, "refresh_rate", None),
            }

    def _run(self):
        frame = [0.0] * self.FRAME_SIZE
        while not self._stop_event.is_set():
            try:
                with self._lock:
                    self.sensor.getFrame(frame)
                if len(frame) != self.FRAME_SIZE or not any(self._finite(frame)):
                    raise ValueError("MLX90640 returned an invalid frame")
                timestamp = time.time()
                with self._lock:
                    self._frame = list(frame)
                    self._updated_at = timestamp
                    callback = self._on_frame
                    recovered = self._last_error is not None
                    self._last_error = None
                if recovered:
                    logger.info("MLX90640 frame acquisition recovered")
                if callback:
                    callback(list(frame), timestamp)
            except Exception as error:
                message = f"{type(error).__name__}: {error}"
                with self._lock:
                    changed = message != self._last_error
                    self._last_error = message
                    callback = self._on_error
                if changed:
                    logger.warning("MLX90640 frame read failed; retrying: %s", message)
                if callback:
                    callback(message)
            self._stop_event.wait(1.0 / max(1, getattr(self, "refresh_rate", 4)))

    @staticmethod
    def _finite(values):
        for value in values:
            try:
                if math.isfinite(float(value)):
                    yield value
            except (TypeError, ValueError):
                continue

