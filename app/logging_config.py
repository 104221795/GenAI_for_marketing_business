import sys
from loguru import logger
from app.config import settings


def setup_logging():
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="14 days",
        level=settings.LOG_LEVEL,
        serialize=True,
    )
    return logger
