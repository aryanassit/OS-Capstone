"""Activity logging. Every module run, input error and bridge call is logged to logs/osim.log."""
import logging
import os
from logging.handlers import RotatingFileHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "osim.log")
_configured = False


def get_logger(name="osim"):
    global _configured
    logger = logging.getLogger("osim")
    if not _configured:
        logger.setLevel(logging.INFO)
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            h = RotatingFileHandler(LOG_FILE, maxBytes=500_000, backupCount=2, encoding="utf-8")
            h.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(module)s | %(message)s"))
            logger.addHandler(h)
        except OSError:
            logger.addHandler(logging.NullHandler())  # read-only disk: keep running
        logger.propagate = False
        _configured = True
    return logger.getChild(name) if name != "osim" else logger
