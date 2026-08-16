import logging
import os
import sys


def configure_logging(level=None):
    """Configure structured stderr logging for terminal use and systemd journald."""
    level_name = (level or os.environ.get("NEOMATRIX_LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        stream=sys.stderr,
        force=True,
    )
    logging.captureWarnings(True)
    return log_level
