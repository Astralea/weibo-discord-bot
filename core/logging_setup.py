import logging
import sys


def setup_logging() -> logging.Logger:
    """Configure logging so that:
    - INFO/WARNING go to stdout (PM2 out.log)
    - ERROR/CRITICAL go to stderr (PM2 error.log)
    - All logs are also written to weibo_bot.log
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers if setup_logging() is called multiple times
    if logger.handlers:
        for h in list(logger.handlers):
            logger.removeHandler(h)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # File handler (all levels)
    file_handler = logging.FileHandler('weibo_bot.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stdout handler (INFO and WARNING)
    class _LessThanErrorFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return record.levelno < logging.ERROR

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.addFilter(_LessThanErrorFilter())
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # Stderr handler (ERROR and above)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    return logging.getLogger(__name__)


