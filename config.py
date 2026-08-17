import copy
import json
import os
from pathlib import Path
import tempfile

DEFAULT_CONFIG = {
    "version": 1,
    "power": True,
    "user_brightness": 0.25,
    "active_mode": None,
    "active_mode_options": {},
    "manual_override_until": None,
    "manual_override_active": False,
    "automation": {
        "enabled": False,
        "sleep_lux": 5.0,
        "wake_lux": 10.0,
        "sleep_dwell_seconds": 60,
        "wake_dwell_seconds": 15,
        "poll_seconds": 5,
        "min_brightness": 0.2,
        "max_lux": 300.0,
        "manual_override_policy": "timed",
        "manual_override_minutes": 30,
    },
    "occupancy": {
        "enabled": False,
        "temperature_delta_f": 4.0,
        "minimum_region_size": 12,
        "absence_dwell_seconds": 60,
        "presence_dwell_seconds": 3,
        "startup_calibration_seconds": 10,
        "edge_exclusion": 1,
    },
}


class ConfigStore:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return copy.deepcopy(DEFAULT_CONFIG)
        try:
            with self.path.open(encoding="utf-8") as handle:
                value = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return copy.deepcopy(DEFAULT_CONFIG)
        return self._merge_defaults(value, copy.deepcopy(DEFAULT_CONFIG))

    def save(self, config):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_path = tempfile.mkstemp(prefix=self.path.name, suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(config, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    @staticmethod
    def _merge_defaults(value, defaults):
        if not isinstance(value, dict):
            return defaults
        for key, default in defaults.items():
            if isinstance(default, dict):
                value[key] = ConfigStore._merge_defaults(value.get(key), default)
            elif key not in value:
                value[key] = default
        return value
