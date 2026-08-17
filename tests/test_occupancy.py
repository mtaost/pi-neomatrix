import unittest

from occupancy import FRAME_HEIGHT, FRAME_SIZE, FRAME_WIDTH, OccupancyDetector


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


def frame_with_region(background=20.0, value=28.0, row_start=8, row_end=14, column_start=12, column_end=18):
    frame = [background] * FRAME_SIZE
    for row in range(row_start, row_end):
        for column in range(column_start, column_end):
            frame[row * FRAME_WIDTH + column] = value
    return frame


class OccupancyDetectorTests(unittest.TestCase):
    def make_detector(self, **settings):
        clock = FakeClock()
        detector = OccupancyDetector({"startup_calibration_seconds": 0, "absence_dwell_seconds": 2, "presence_dwell_seconds": 2, **settings}, clock=clock)
        return detector, clock

    def test_empty_room_and_human_sized_warm_region(self):
        detector, clock = self.make_detector(minimum_region_size=12)
        detector.process([20.0] * FRAME_SIZE, 100)
        self.assertFalse(detector.state()["present"])
        clock.value = 1
        detector.process(frame_with_region(), 101)
        clock.value = 3
        state = detector.process(frame_with_region(), 103)
        self.assertTrue(state["present"])
        self.assertGreater(state["confidence"], 0)

    def test_small_hot_object_does_not_trigger_presence(self):
        detector, clock = self.make_detector(minimum_region_size=12)
        detector.process(frame_with_region(row_start=10, row_end=12, column_start=15, column_end=17), 100)
        clock.value = 5
        state = detector.process(frame_with_region(row_start=10, row_end=12, column_start=15, column_end=17), 105)
        self.assertFalse(state["present"])
        self.assertEqual(state["largest_region"], 4)

    def test_relative_background_drift_is_handled(self):
        detector, clock = self.make_detector(minimum_region_size=12)
        detector.process(frame_with_region(background=20, value=28), 100)
        clock.value = 2
        state = detector.process(frame_with_region(background=24, value=32), 102)
        self.assertTrue(state["present"])
        self.assertAlmostEqual(state["background_temperature"], 24.0)

    def test_absence_hysteresis_and_invalid_frame_diagnostics(self):
        detector, clock = self.make_detector(minimum_region_size=12)
        detector.process(frame_with_region(), 100)
        clock.value = 2
        detector.process(frame_with_region(), 102)
        self.assertTrue(detector.state()["present"])
        clock.value = 3
        detector.process([20.0] * FRAME_SIZE, 103)
        clock.value = 5
        state = detector.process([20.0] * FRAME_SIZE, 105)
        self.assertFalse(state["present"])
        state = detector.process([None] * FRAME_SIZE, 106)
        self.assertIn("no finite", state["error"])


if __name__ == "__main__":
    unittest.main()
