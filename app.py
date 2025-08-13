import sys
from core.logging_setup import setup_logging
from core.config import load_config
from services.weibo_scraper import WeiboScraper


logger = setup_logging()


def main() -> int:
    config = load_config()
    scraper = WeiboScraper(config=config, account_names='auto')
    try:
        scraper.start()
        return 0
    except KeyboardInterrupt:
        logger.info("\nStopping scraper...")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1
    finally:
        try:
            scraper.cleanup()
        except Exception:
            pass
        print("Bot stopped.")


if __name__ == '__main__':
    sys.exit(main())


