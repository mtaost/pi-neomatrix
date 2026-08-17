import time
import unittest

from display_modes.thermalcamera import ThermalCamera
from thermal_sensor import ThermalSensorService


class FakeDriver:
    width = 16
    height = 16


class FakeSensor:
    serial_number = (1, 2, 3)

    def __init__(self):
        self.refresh_rate = None
        self.calls = 0

    def getFrame(self, frame):
        self.calls += 1
        frame[:] = [20.0 + (index % 8) / 10 for index in range(768)]


class ThermalSensorServiceTests(unittest.TestCase):
    def test_service_publishes_latest_frame_and_callbacks(self):
        sensor = FakeSensor()
        frames = []
        service = ThermalSensorService(sensor=sensor, on_frame=lambda frame, timestamp: frames.append((frame, timestamp)))
        service.start()
        deadline = time.time() + 1
        while time.time() < deadline and not frames:
            time.sleep(0.01)
        service.stop()
        self.assertTrue(frames)
        latest = service.get_latest_frame()
        self.assertEqual(len(latest[0]), 768)
        self.assertEqual(sensor.refresh_rate, 4)
        self.assertIsNone(service.status()["error"])

    def test_thermal_mode_consumes_shared_service_without_sensor_ownership(self):
        service = ThermalSensorService(sensor=FakeSensor())
        service._frame = [20.0 + (index % 8) / 10 for index in range(768)]
        service._updated_at = time.time()
        mode = ThermalCamera(FakeDriver(), {"thermal_service": service}, thermal_service=service)
        self.assertTrue(mode._read_frame())
        mode._render_frame()
        self.assertIsNone(mode.mlx)
        self.assertGreater(len(set(mode.image.getdata())), 1)


if __name__ == "__main__":
    unittest.main()
