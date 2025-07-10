import logging
from typing import TextIO

def Logger(name: str) -> logging.Logger:
    console_handler: logging.StreamHandler[TextIO] = logging.StreamHandler();
    file_handler: logging.FileHandler = logging.FileHandler(
        filename="./logs/logs.txt",
        encoding="utf-8",
        mode='w'
    )

    formatter: logging.Formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s.%(funcName)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger: logging.Logger = logging.getLogger(name)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)

    return logger
