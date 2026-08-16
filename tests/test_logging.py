import logging
import sys
import unittest
from unittest import mock

from logging_setup import configure_logging


class LoggingSetupTests(unittest.TestCase):
    @mock.patch("logging_setup.logging.captureWarnings")
    @mock.patch("logging_setup.logging.basicConfig")
    @mock.patch.dict("logging_setup.os.environ", {"NEOMATRIX_LOG_LEVEL": "debug"}, clear=False)
    def test_configures_timestamped_stderr_logging(self, basic_config, capture_warnings):
        self.assertEqual(configure_logging(), logging.DEBUG)
        basic_config.assert_called_once_with(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
            stream=sys.stderr,
            force=True,
        )
        capture_warnings.assert_called_once_with(True)


if __name__ == "__main__":
    unittest.main()
