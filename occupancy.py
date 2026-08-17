"""Hardware-independent occupancy detection for MLX90640 frames."""

import math
import statistics
import time


FRAME_WIDTH = 32
FRAME_HEIGHT = 24
FRAME_SIZE = FRAME_WIDTH * FRAME_HEIGHT


DEFAULT_OCCUPANCY_SETTINGS = {
    "temperature_delta_f": 4.0,
    "minimum_region_size": 12,
    "absence_dwell_seconds": 60,
    "presence_dwell_seconds": 3,
    "startup_calibration_seconds": 10,
    "edge_exclusion": 1,
}


def _finite_values(frame):
    if not isinstance(frame, (list, tuple)) or len(frame) != FRAME_SIZE:
        raise ValueError(f"Thermal frame must contain {FRAME_SIZE} values.")
    values = []
    for value in frame:
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            values.append(value)
    if not values:
        raise ValueError("Thermal frame contains no finite temperatures.")
    return values


class OccupancyDetector:
    """Classify thermal frames using relative warmth and connected regions."""

    def __init__(self, settings=None, clock=None):
        self._clock = clock or time.monotonic
        self.settings = dict(DEFAULT_OCCUPANCY_SETTINGS)
        self._calibration_started = None
        self._present = False
        self._candidate_since = None
        self._candidate_value = None
        self._state = {
            "present": False,
            "confidence": 0.0,
            "warm_pixels": 0,
            "largest_region": 0,
            "background_temperature": None,
            "maximum_temperature": None,
            "updated_at": None,
            "calibrating": True,
            "error": None,
        }
        self.update_settings(settings or {})

    def update_settings(self, values):
        if not isinstance(values, dict):
            raise ValueError("Occupancy settings must be an object.")
        unknown = set(values) - set(DEFAULT_OCCUPANCY_SETTINGS)
        if unknown:
            raise ValueError(f"Unknown occupancy setting: {sorted(unknown)[0]}")
        settings = dict(self.settings)
        for key, value in values.items():
            if key == "temperature_delta_f":
                value = self._number(key, value, 0.5, 20.0)
            elif key == "minimum_region_size":
                value = self._integer(key, value, 1, FRAME_SIZE)
            elif key in {"absence_dwell_seconds", "presence_dwell_seconds"}:
                value = self._integer(key, value, 1, 86400)
            elif key == "startup_calibration_seconds":
                value = self._integer(key, value, 0, 86400)
            elif key == "edge_exclusion":
                value = self._integer(key, value, 0, min(FRAME_WIDTH, FRAME_HEIGHT) // 2)
            settings[key] = value
        self.settings = settings
        self._candidate_since = None
        self._candidate_value = None
        return dict(self.settings)

    @staticmethod
    def _number(key, value, minimum, maximum):
        try:
            value = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{key} must be numeric.") from error
        if not minimum <= value <= maximum:
            raise ValueError(f"{key} must be from {minimum} to {maximum}.")
        return value

    @staticmethod
    def _integer(key, value, minimum, maximum):
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{key} must be numeric.") from error
        if not number.is_integer() or not minimum <= number <= maximum:
            raise ValueError(f"{key} must be an integer from {minimum} to {maximum}.")
        return int(number)

    def process(self, frame, timestamp=None):
        timestamp = time.time() if timestamp is None else float(timestamp)
        now = self._clock()
        try:
            values = _finite_values(frame)
            background = statistics.median(values)
            maximum = max(values)
            threshold = self.settings["temperature_delta_f"] / 1.8
            if self._present:
                threshold *= 0.65
            warm = self._warm_mask(frame, background + threshold)
            regions = self._regions(warm)
            warm_pixels = sum(warm)
            largest_region = max(regions, default=0)
            minimum_region = self.settings["minimum_region_size"]
            candidate = largest_region >= minimum_region
            confidence = min(1.0, largest_region / max(1.0, minimum_region * 4.0))

            if self._calibration_started is None:
                self._calibration_started = now
            calibrating = now - self._calibration_started < self.settings["startup_calibration_seconds"]
            if not calibrating:
                self._apply_candidate(candidate, now)
            else:
                self._candidate_since = None
                self._candidate_value = None
                self._present = False

            self._state = {
                "present": self._present,
                "confidence": round(confidence, 3),
                "warm_pixels": warm_pixels,
                "largest_region": largest_region,
                "background_temperature": round(background, 2),
                "maximum_temperature": round(maximum, 2),
                "updated_at": timestamp,
                "calibrating": calibrating,
                "error": None,
            }
        except ValueError as error:
            self._state = dict(self._state)
            self._state.update({"updated_at": timestamp, "error": str(error)})
        return self.state()

    def _apply_candidate(self, candidate, now):
        if candidate != self._candidate_value:
            self._candidate_value = candidate
            self._candidate_since = now
            return
        dwell = self.settings["presence_dwell_seconds"] if candidate else self.settings["absence_dwell_seconds"]
        if now - self._candidate_since >= dwell:
            self._present = candidate

    def _warm_mask(self, frame, threshold):
        edge = self.settings["edge_exclusion"]
        mask = [False] * FRAME_SIZE
        for index, value in enumerate(frame):
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
            row, column = divmod(index, FRAME_WIDTH)
            if edge and (row < edge or row >= FRAME_HEIGHT - edge or column < edge or column >= FRAME_WIDTH - edge):
                continue
            mask[index] = math.isfinite(value) and value > threshold
        return mask

    @staticmethod
    def _regions(mask):
        seen = set()
        regions = []
        for start, is_warm in enumerate(mask):
            if not is_warm or start in seen:
                continue
            stack = [start]
            seen.add(start)
            size = 0
            while stack:
                index = stack.pop()
                size += 1
                row, column = divmod(index, FRAME_WIDTH)
                for row_offset in (-1, 0, 1):
                    for column_offset in (-1, 0, 1):
                        if not row_offset and not column_offset:
                            continue
                        neighbor_row = row + row_offset
                        neighbor_column = column + column_offset
                        if not (0 <= neighbor_row < FRAME_HEIGHT and 0 <= neighbor_column < FRAME_WIDTH):
                            continue
                        neighbor = neighbor_row * FRAME_WIDTH + neighbor_column
                        if mask[neighbor] and neighbor not in seen:
                            seen.add(neighbor)
                            stack.append(neighbor)
            regions.append(size)
        return regions

    def state(self):
        return dict(self._state)
