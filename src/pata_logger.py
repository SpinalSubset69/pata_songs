import logging
from os import getenv, path, makedirs
from typing import TextIO

from dotenv import load_dotenv

makedirs("logs", exist_ok=True)

load_dotenv()

LOG_LEVEL: str = getenv("LOG_LEVEL", "INFO")


def Logger(name: str) -> logging.Logger:
    console_handler: logging.StreamHandler[TextIO] = logging.StreamHandler()
    file_handler: logging.FileHandler = logging.FileHandler(
        filename=path.join("logs", "logs.txt"), encoding="utf-8", mode="w"
    )

    formatter: logging.Formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s.%(funcName)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger: logging.Logger = logging.getLogger(name)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    log_level = logging._nameToLevel.get(LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    return logger
