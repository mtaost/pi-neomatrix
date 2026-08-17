import argparse
import atexit
import logging
import os
from pathlib import Path

import driver
from assets import AssetCatalog
from config import ConfigStore
from controller import DisplayController
from lifecycle import install_shutdown_handlers
from logging_setup import configure_logging
from sensors import BH1750Sensor, SensorService
from thermal_sensor import ThermalSensorService
from webserver.app import create_app


ROOT = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)


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
        logger.exception("Controller initialization failed; releasing the matrix driver")
        matrix_driver.stop()
        raise
    try:
        sensor = BH1750Sensor()
        service = SensorService(sensor, controller.record_sensor_reading, controller.record_sensor_error, controller.poll_seconds)
        controller.attach_sensor_service(service, available=True, name=sensor.name)
    except Exception as error:
        controller.attach_sensor_service(None, available=False, name="BH1750", error=str(error))
    try:
        thermal_service = ThermalSensorService(on_frame=controller.record_thermal_frame, on_error=controller.record_thermal_error)
        controller.attach_thermal_service(thermal_service, available=True)
    except Exception as error:
        controller.attach_thermal_service(None, available=False, name="MLX90640", error=str(error))
    return controller


def main():
    configure_logging()
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
        logger.info("Starting NeoMatrix web service on %s:%s", args.host, args.port)
        from waitress import serve
        serve(app, host=args.host, port=args.port)
    except Exception:
        logger.exception("NeoMatrix service exited due to an unexpected error")
        raise
    finally:
        if controller:
            logger.info("Shutting down NeoMatrix service")
            controller.shutdown()


if __name__ == "__main__":
    main()
