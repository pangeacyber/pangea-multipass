import json
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Dict, Optional


def data_load(filename: str) -> Optional[dict]:
    if not os.path.exists(filename):
        return None

    with open(filename, "r") as f:
        return json.load(f)


def data_save(filename: str, data: dict):
    with open(filename, "w") as f:
        json.dump(data, f)


_loggers: Dict[str, bool] = {}


def set_logger(logger_name: str, level=logging.DEBUG):
    if _loggers.get(logger_name) is not None:
        return

    _loggers[logger_name] = True
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    handler = TimedRotatingFileHandler(
        filename="multipass_logs.json", when="D", interval=1, backupCount=90, encoding="utf-8", delay=False
    )
    handler.setLevel(level)
    formatter = logging.Formatter(
        fmt='{"time": "%(asctime)s.%(msecs)03d", "name": "%(name)s", "level": "%(levelname)s",  "message": %(message)s },',
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
