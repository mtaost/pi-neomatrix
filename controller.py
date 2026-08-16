import copy
import threading
import time

from PIL import Image

from assets import AssetCatalog
from config import ConfigStore
from layers import BrightnessLayer, SleepLayer
from modes import build_mode_registry


class DisplayController:
    def __init__(self, driver, config_store, asset_catalog, registry=None, render_fps=30):
        self.driver = driver
        self.config_store = config_store
        self.assets = asset_catalog
        self.registry = registry or build_mode_registry()
        self.render_interval = 1.0 / render_fps
        self.layers = (SleepLayer(), BrightnessLayer())
        self._lock = threading.RLock()
        self._config = self.config_store.load()
        self._frame = Image.new("RGB", (driver.width, driver.height), "black")
        self._active_mode = None
        self._active_mode_id = None
        self._mode_thread = None
        self._mode_stop_event = None
        self._mode_pause_event = None
        self._render_stop_event = threading.Event()
        self._render_thread = None
        self._sensor_service = None
        self._shutdown = False
        self._sensor = {"available": False, "name": "BH1750", "lux": None, "updated_at": None, "error": "Sensor not initialized"}
        self._sleeping = False
        self._dark_since = None
        self._bright_since = None
        if hasattr(driver, "set_brightness"):
            driver.set_brightness(1.0)

    def start(self):
        if self._render_thread is None:
            self._render_thread = threading.Thread(target=self._render_loop, name="display-compositor", daemon=True)
            self._render_thread.start()
        if self._sensor_service:
            self._sensor_service.start()
        mode_id = self._config.get("active_mode")
        if mode_id:
            try:
                options = self._config.get("active_mode_options", {})
                self.select_mode(mode_id, options.get("asset_id"), manual=False)
            except (ValueError, RuntimeError):
                pass

    def shutdown(self):
        with self._lock:
            if self._shutdown:
                return
            self._shutdown = True
            sensor_service = self._sensor_service
            self._stop_active_locked()
            self._render_stop_event.set()
        if sensor_service:
            sensor_service.stop()
        if self._render_thread:
            self._render_thread.join(timeout=2)
        self._show_black()
        if hasattr(self.driver, "stop"):
            self.driver.stop()

    def attach_sensor_service(self, service, available=True, name="BH1750", error=None):
        with self._lock:
            self._sensor_service = service
            self._sensor.update({"available": available, "name": name, "error": error})

    def record_sensor_reading(self, lux, timestamp=None):
        with self._lock:
            self._sensor.update({"available": True, "lux": float(lux), "updated_at": timestamp or time.time(), "error": None})

    def record_sensor_error(self, message):
        with self._lock:
            self._sensor["error"] = str(message)

    def poll_seconds(self):
        with self._lock:
            return self._config["automation"]["poll_seconds"]

    def list_modes(self):
        return [spec.to_dict() for spec in self.registry.values()]

    def list_assets(self):
        return self.assets.list_assets()

    def select_mode(self, mode_id, asset_id=None, manual=True):
        if mode_id not in self.registry:
            raise ValueError("Unknown display mode.")
        spec = self.registry[mode_id]
        options = {}
        if spec.requires_asset:
            path = self.assets.resolve(asset_id)
            options = {"asset_id": asset_id, "asset_path": path}
        elif asset_id is not None:
            raise ValueError("This display mode does not accept an image asset.")
        try:
            mode = spec.factory(self.driver, options)
        except Exception as error:
            raise RuntimeError(f"Unable to start {spec.name}: {error}") from error
        stop_event = threading.Event()
        pause_event = threading.Event()
        mode.frame_sink = self.publish_frame
        mode.stop_event = stop_event
        mode.pause_event = pause_event
        with self._lock:
            self._stop_active_locked()
            self._active_mode = mode
            self._active_mode_id = mode_id
            self._mode_stop_event = stop_event
            self._mode_pause_event = pause_event
            self._frame = Image.new("RGB", (self.driver.width, self.driver.height), "black")
            self._config["active_mode"] = mode_id
            self._config["active_mode_options"] = {"asset_id": asset_id} if asset_id else {}
            self._config["power"] = True
            if manual:
                self._record_manual_interaction_locked()
            self._persist_locked()
            self._mode_thread = threading.Thread(target=mode.run, name=f"mode-{mode_id}", daemon=True)
            self._mode_thread.start()
        return self.get_state()

    def set_power(self, on):
        if not isinstance(on, bool):
            raise ValueError("Power must be a boolean.")
        with self._lock:
            self._config["power"] = on
            if on:
                self._record_manual_interaction_locked()
            else:
                self._config["manual_override_active"] = False
                self._config["manual_override_until"] = None
            self._persist_locked()
        return self.get_state()

    def set_user_brightness(self, brightness):
        try:
            brightness = float(brightness)
        except (TypeError, ValueError) as error:
            raise ValueError("Brightness must be a number from 0 to 1.") from error
        if not 0 <= brightness <= 1:
            raise ValueError("Brightness must be a number from 0 to 1.")
        with self._lock:
            self._config["user_brightness"] = brightness
            self._record_manual_interaction_locked()
            self._persist_locked()
        return self.get_state()

    def update_settings(self, changes):
        if not isinstance(changes, dict):
            raise ValueError("Settings must be a JSON object.")
        unknown = set(changes) - {"brightness", "automation"}
        if unknown:
            raise ValueError(f"Unknown setting: {sorted(unknown)[0]}")
        with self._lock:
            if "brightness" in changes:
                self._set_brightness_locked(changes["brightness"])
                self._record_manual_interaction_locked()
            if "automation" in changes:
                self._update_automation_locked(changes["automation"])
            self._persist_locked()
        return self.get_state()

    def get_state(self):
        with self._lock:
            now = time.time()
            effective_brightness, sleep_reason = self._policy_locked(now)
            return {
                "mode": self._active_mode_id,
                "mode_options": copy.deepcopy(self._config["active_mode_options"]),
                "power": self._config["power"],
                "user_brightness": self._config["user_brightness"],
                "effective_brightness": effective_brightness,
                "sleeping": self._sleeping,
                "sleep_reason": sleep_reason,
                "automation": copy.deepcopy(self._config["automation"]),
                "manual_override": self._manual_override_state_locked(now),
                "sensor": copy.deepcopy(self._sensor),
            }

    def publish_frame(self, image):
        with self._lock:
            self._frame = image.convert("RGB").copy()

    def _render_loop(self):
        while not self._render_stop_event.is_set():
            with self._lock:
                brightness, _ = self._policy_locked(time.time())
                image = self._frame.copy()
                sleeping = self._sleeping
            context = {"sleeping": sleeping, "brightness": brightness}
            for layer in self.layers:
                image = layer.apply(image, context)
            self.driver.display(image)
            self._render_stop_event.wait(self.render_interval)

    def _show_black(self):
        self.driver.display(Image.new("RGB", (self.driver.width, self.driver.height), "black"))

    def _policy_locked(self, now):
        if not self._config["power"]:
            self._set_sleeping_locked(True)
            return 0.0, "manual_off"
        automation = self._config["automation"]
        sensor_lux = self._sensor["lux"]
        if not automation["enabled"] or sensor_lux is None:
            self._set_sleeping_locked(False)
            return self._config["user_brightness"], "automation_disabled" if not automation["enabled"] else "sensor_unavailable"
        override = self._manual_override_state_locked(now)
        if override["active"]:
            self._set_sleeping_locked(False)
            return self._ambient_brightness_locked(sensor_lux), "manual_override"
        if self._sleeping:
            if sensor_lux >= automation["wake_lux"]:
                self._bright_since = self._bright_since or now
                if now - self._bright_since >= automation["wake_dwell_seconds"]:
                    self._set_sleeping_locked(False)
            else:
                self._bright_since = None
        else:
            if sensor_lux <= automation["sleep_lux"]:
                self._dark_since = self._dark_since or now
                if now - self._dark_since >= automation["sleep_dwell_seconds"]:
                    self._set_sleeping_locked(True)
            else:
                self._dark_since = None
        return (0.0 if self._sleeping else self._ambient_brightness_locked(sensor_lux), "ambient_dark" if self._sleeping else "ambient_active")

    def _set_sleeping_locked(self, sleeping):
        self._sleeping = sleeping
        if self._mode_pause_event:
            if sleeping:
                self._mode_pause_event.set()
            else:
                self._mode_pause_event.clear()

    def _ambient_brightness_locked(self, lux):
        automation = self._config["automation"]
        maximum = self._config["user_brightness"]
        minimum = min(maximum, automation["min_brightness"])
        span = max(1.0, automation["max_lux"] - automation["wake_lux"])
        ratio = min(1.0, max(0.0, (lux - automation["wake_lux"]) / span))
        return minimum + (maximum - minimum) * ratio

    def _manual_override_state_locked(self, now):
        automation = self._config["automation"]
        policy = automation["manual_override_policy"]
        if policy == "always":
            return {"active": False, "policy": policy, "until": None}
        if policy == "manual":
            return {"active": bool(self._config["manual_override_active"]), "policy": policy, "until": None}
        until = self._config.get("manual_override_until")
        active = bool(until and now < until)
        if not active and until:
            self._config["manual_override_until"] = None
            self._config["manual_override_active"] = False
            self._persist_locked()
        return {"active": active, "policy": policy, "until": until if active else None}

    def _record_manual_interaction_locked(self):
        automation = self._config["automation"]
        policy = automation["manual_override_policy"]
        if policy == "timed":
            self._config["manual_override_until"] = time.time() + 60 * automation["manual_override_minutes"]
            self._config["manual_override_active"] = True
        elif policy == "manual":
            self._config["manual_override_until"] = None
            self._config["manual_override_active"] = True
        else:
            self._config["manual_override_until"] = None
            self._config["manual_override_active"] = False

    def _set_brightness_locked(self, value):
        try:
            value = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError("Brightness must be a number from 0 to 1.") from error
        if not 0 <= value <= 1:
            raise ValueError("Brightness must be a number from 0 to 1.")
        self._config["user_brightness"] = value

    def _update_automation_locked(self, values):
        if not isinstance(values, dict):
            raise ValueError("Automation settings must be an object.")
        allowed = {"enabled", "sleep_lux", "wake_lux", "sleep_dwell_seconds", "wake_dwell_seconds", "poll_seconds", "min_brightness", "max_lux", "manual_override_policy", "manual_override_minutes"}
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"Unknown automation setting: {sorted(unknown)[0]}")
        automation = self._config["automation"]
        for key, value in values.items():
            if key == "enabled":
                if not isinstance(value, bool):
                    raise ValueError("Automation enabled must be a boolean.")
            elif key == "manual_override_policy":
                if value not in {"always", "timed", "manual"}:
                    raise ValueError("Manual override policy must be always, timed, or manual.")
            else:
                try:
                    value = float(value)
                except (TypeError, ValueError) as error:
                    raise ValueError(f"{key} must be numeric.") from error
                if value < 0:
                    raise ValueError(f"{key} cannot be negative.")
                if key in {"sleep_dwell_seconds", "wake_dwell_seconds", "poll_seconds", "manual_override_minutes"}:
                    value = int(value)
                    if value < 1:
                        raise ValueError(f"{key} must be at least 1.")
                if key == "min_brightness" and value > 1:
                    raise ValueError("min_brightness must be from 0 to 1.")
            automation[key] = value
        if automation["wake_lux"] <= automation["sleep_lux"]:
            raise ValueError("wake_lux must be greater than sleep_lux.")
        if automation["max_lux"] <= automation["wake_lux"]:
            raise ValueError("max_lux must be greater than wake_lux.")
        self._dark_since = None
        self._bright_since = None
        if "manual_override_policy" in values:
            self._record_manual_interaction_locked()

    def _persist_locked(self):
        self.config_store.save(self._config)

    def _stop_active_locked(self):
        mode, thread, stop_event, pause_event = self._active_mode, self._mode_thread, self._mode_stop_event, self._mode_pause_event
        self._active_mode = self._active_mode_id = self._mode_thread = self._mode_stop_event = self._mode_pause_event = None
        if stop_event:
            stop_event.set()
        if pause_event:
            pause_event.clear()
        if thread and thread.is_alive():
            thread.join(timeout=2)
        if mode:
            try:
                mode.cleanup()
            except Exception:
                pass
