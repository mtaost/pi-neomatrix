import json
import tempfile
import time
import unittest
from pathlib import Path

from PIL import Image

from assets import AssetCatalog
from config import ConfigStore
from controller import DisplayController
from modes import ModeSpec


class FakeDriver:
    width = 16
    height = 16

    def __init__(self):
        self.frames = []
        self.brightness = None
        self.stopped = False

    def set_brightness(self, value):
        self.brightness = value

    def display(self, image):
        self.frames.append(image.copy())

    def stop(self):
        self.stopped = True


class FakeMode:
    def __init__(self, driver):
        self.driver = driver
        self.frame_sink = None
        self.stop_event = None
        self.pause_event = None
        self.cleaned = False

    def run(self):
        self.frame_sink(Image.new("RGB", (self.driver.width, self.driver.height), "red"))
        self.stop_event.wait(2)

    def cleanup(self):
        self.cleaned = True


def fake_factory(driver, options):
    return FakeMode(driver)


class ConfigAndAssetTests(unittest.TestCase):
    def test_config_defaults_and_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            store = ConfigStore(path)
            self.assertFalse(store.load()["automation"]["enabled"])
            path.write_text("not json", encoding="utf-8")
            self.assertEqual(store.load()["automation"]["wake_lux"], 10.0)
            config = store.load()
            config["user_brightness"] = 0.7
            store.save(config)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["user_brightness"], 0.7)

    def test_asset_catalog_rejects_escape_and_lists_supported_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "res"
            root.mkdir()
            (root / "ok.gif").write_bytes(b"gif")
            (root / "ignore.txt").write_text("x", encoding="utf-8")
            catalog = AssetCatalog(root)
            self.assertEqual(catalog.list_assets(), [{"id": "ok.gif", "name": "ok.gif"}])
            self.assertEqual(catalog.resolve("ok.gif"), (root / "ok.gif").resolve())
            with self.assertRaises(ValueError):
                catalog.resolve("../outside.gif")


class DisplayControllerTests(unittest.TestCase):
    def make_controller(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        assets = root / "res"
        assets.mkdir()
        (assets / "sample.gif").write_bytes(b"gif")
        registry = {
            "fake": ModeSpec("fake", "Fake", fake_factory),
            "image": ModeSpec("image", "Image", fake_factory, requires_asset=True),
        }
        controller = DisplayController(FakeDriver(), ConfigStore(root / "config.json"), AssetCatalog(assets), registry, render_fps=100)
        self.addCleanup(controller.shutdown)
        return controller

    def test_select_mode_publishes_frames_and_persists_state(self):
        controller = self.make_controller()
        controller.start()
        state = controller.select_mode("fake")
        self.assertEqual(state["mode"], "fake")
        time.sleep(0.03)
        self.assertTrue(controller.driver.frames)
        self.assertEqual(controller.config_store.load()["active_mode"], "fake")

    def test_image_requires_an_approved_asset(self):
        controller = self.make_controller()
        with self.assertRaises(ValueError):
            controller.select_mode("image")
        controller.select_mode("image", "sample.gif")
        self.assertEqual(controller.get_state()["mode"], "image")

    def test_automation_dwell_and_manual_override(self):
        controller = self.make_controller()
        controller.update_settings({"automation": {"enabled": True, "sleep_lux": 5, "wake_lux": 10, "sleep_dwell_seconds": 1, "wake_dwell_seconds": 1, "poll_seconds": 1, "min_brightness": 0.2, "max_lux": 100, "manual_override_policy": "always", "manual_override_minutes": 1}})
        controller.record_sensor_reading(4, 100)
        with controller._lock:
            controller._policy_locked(100)
            brightness, reason = controller._policy_locked(101.1)
        self.assertEqual(brightness, 0)
        self.assertEqual(reason, "ambient_dark")
        controller.record_sensor_reading(12, 102)
        with controller._lock:
            controller._policy_locked(102)
            brightness, reason = controller._policy_locked(103.1)
        self.assertGreater(brightness, 0)
        self.assertEqual(reason, "ambient_active")
        controller.update_settings({"automation": {"manual_override_policy": "manual"}})
        controller.set_user_brightness(0.5)
        controller.record_sensor_reading(0, 104)
        self.assertEqual(controller.get_state()["sleep_reason"], "manual_override")


try:
    from webserver.app import create_app
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


@unittest.skipUnless(FLASK_AVAILABLE, "Flask is not installed in this environment")
class ApiTests(unittest.TestCase):
    def test_api_validates_mode_and_power_requests(self):
        controller = DisplayController(FakeDriver(), ConfigStore(Path(tempfile.gettempdir()) / "neomatrix-api-test.json"), AssetCatalog(Path(tempfile.gettempdir()) / "none"), {"fake": ModeSpec("fake", "Fake", fake_factory)})
        self.addCleanup(controller.shutdown)
        client = create_app(controller).test_client()
        self.assertIn(b"Display modes", client.get("/").data)
        self.assertIn(b"Ambient automation", client.get("/automation").data)
        self.assertEqual(client.get("/api/state").get_json()["error"], None)
        self.assertEqual(client.post("/api/mode", json={"mode": "unknown"}).status_code, 400)
        self.assertEqual(client.post("/api/power", json={"on": "yes"}).status_code, 400)
        self.assertEqual(client.patch("/api/settings", json={"brightness": 2}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
