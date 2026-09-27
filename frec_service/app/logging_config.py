# app/logging_config.py

import os
import logging
from logging.handlers import RotatingFileHandler


def setup_logging(log_dir="logs", log_file="api.log", level=logging.DEBUG):
    os.makedirs(log_dir, exist_ok=True)

    file_path = os.path.join(log_dir, log_file)

    file_handler = RotatingFileHandler(file_path, maxBytes=1_000_000, backupCount=5)
    file_handler.setLevel(level)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)

    # Optional: also log to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    logging.debug("Logging has been set up.")
