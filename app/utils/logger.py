"""
Centralized logging configuration using Loguru.
Replaces standard logging for better async handling and colorized output.
"""
import sys
import logging
from pathlib import Path
from loguru import logger
from app.config import settings


class InterceptHandler(logging.Handler):
    """
    Intercepts standard logging messages (e.g., from Uvicorn or Twilio)
    and routes them through Loguru for consistent formatting.
    """
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logger():
    """
    Configures the global logger with both console and file outputs.
    """
    # 1. Remove default handlers to prevent duplicates
    logger.remove()

    # 2. Add colorized console handler for development
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        colorize=True,
        enqueue=True,  # Makes logging thread-safe and async-friendly
    )

    # 3. Add file handler for production (rotates daily, keeps 30 days)
    if settings.ENVIRONMENT == "production":
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.log",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="00:00",  # Rotate at midnight
            retention="30 days",  # Keep logs for 30 days
            compression="zip",  # Compress old logs
            enqueue=True,
            serialize=False,  # Set to True for JSON logs (useful for log aggregation)
        )

        # In production section
        logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.json",
            level="INFO",
            format="{message}",
            rotation="00:00",
            retention="30 days",
            serialize=True,  # JSON format
            enqueue=True,
            compression="zip",
        )
        
        # Separate error log file
        logger.add(
            log_dir / "errors_{time:YYYY-MM-DD}.log",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="00:00",
            retention="90 days",  # Keep error logs longer
            compression="zip",
            enqueue=True,
            backtrace=True,  # Include full traceback
            diagnose=True,   # Include variable values
        )

    # 4. Hijack standard logging (so Uvicorn/FastAPI logs look nice too)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # 5. Configure third-party loggers
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False
    
    logger.info(f"Logger configured for {settings.ENVIRONMENT} environment")
    
    return logger


# Configure immediately on import
configured_logger = setup_logger()

# Export 'logger' so other files can just do: "from app.utils.logger import logger"
__all__ = ["logger"]