import argparse
import atexit
import os
from pathlib import Path

import driver
from assets import AssetCatalog
from config import ConfigStore
from controller import DisplayController
from lifecycle import install_shutdown_handlers
from sensors import BH1750Sensor, SensorService
from webserver.app import create_app


ROOT = Path(__file__).resolve().parent


def build_controller(config_path=None, driver_factory=driver.MatrixDriver):
    config_path = config_path or os.environ.get("NEOMATRIX_CONFIG", ROOT / "neomatrix-config.json")
    matrix_driver = driver_factory()
    try:
        controller = DisplayController(
            matrix_driver,
            ConfigStore(config_path),
            AssetCatalog(ROOT / "res"),
        )
    except Exception:
        matrix_driver.stop()
        raise
    try:
        sensor = BH1750Sensor()
        service = SensorService(sensor, controller.record_sensor_reading, controller.record_sensor_error, controller.poll_seconds)
        controller.attach_sensor_service(service, available=True, name=sensor.name)
    except Exception as error:
        controller.attach_sensor_service(None, available=False, name="BH1750", error=str(error))
    return controller


def main():
    parser = argparse.ArgumentParser(description="pi-neomatrix mobile display control service")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args()

    controller = None
    try:
        controller = build_controller()
        atexit.register(controller.shutdown)
        install_shutdown_handlers(controller.shutdown)
        app = create_app(controller)
        controller.start()
        from waitress import serve
        serve(app, host=args.host, port=args.port)
    finally:
        if controller:
            controller.shutdown()


if __name__ == "__main__":
    main()
