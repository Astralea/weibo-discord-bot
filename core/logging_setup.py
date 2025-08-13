import logging


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('weibo_bot.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


