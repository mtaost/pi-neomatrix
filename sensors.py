import logging
import threading
import time


logger = logging.getLogger(__name__)


class Sensor:
    name = "sensor"

    def read_lux(self):
        raise NotImplementedError


class BH1750Sensor(Sensor):
    name = "BH1750"

    def __init__(self):
        import board
        import busio
        import adafruit_bh1750
        self._i2c = busio.I2C(board.SCL, board.SDA)
        self._sensor = adafruit_bh1750.BH1750(self._i2c)

    def read_lux(self):
        return float(self._sensor.lux)


class SensorService:
    def __init__(self, sensor, on_reading, on_error, poll_seconds):
        self.sensor = sensor
        self._on_reading = on_reading
        self._on_error = on_error
        self._poll_seconds = poll_seconds
        self._stop_event = threading.Event()
        self._thread = None
        self._last_error = None

    def start(self):
        if self._thread is None:
            logger.info("Starting sensor service: %s", self.sensor.name)
            self._thread = threading.Thread(target=self._run, name="light-sensor", daemon=True)
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("Sensor service stopped: %s", self.sensor.name)

    def _run(self):
        while not self._stop_event.is_set():
            try:
                self._on_reading(float(self.sensor.read_lux()), time.time())
                if self._last_error is not None:
                    logger.info("Sensor recovered: %s", self.sensor.name)
                    self._last_error = None
            except Exception as error:
                message = str(error)
                if message != self._last_error:
                    logger.warning("Sensor read failed (%s): %s", self.sensor.name, message)
                    self._last_error = message
                self._on_error(message)
            self._stop_event.wait(max(1.0, float(self._poll_seconds())))
