from __future__ import annotations

import logging
from typing import Dict, Any

import toml


logger = logging.getLogger(__name__)


def load_config() -> Dict[str, Any]:
    try:
        config = toml.load('config.toml')

        if 'weibo' not in config:
            raise ValueError("Missing 'weibo' section in config.toml")
        if 'status' not in config:
            raise ValueError("Missing 'status' section in config.toml")

        for account_name, account_config in config['weibo'].items():
            if 'message_webhook' not in account_config:
                raise ValueError(f"Missing message_webhook for account {account_name}")
            webhook_url = account_config['message_webhook']
            if not webhook_url.startswith('https://discord.com/api/webhooks/'):
                raise ValueError(f"Invalid Discord webhook URL for account {account_name}")

        if 'message_webhook' not in config['status']:
            raise ValueError("Missing status message_webhook in config.toml")
        if not config['status']['message_webhook'].startswith('https://discord.com/api/webhooks/'):
            raise ValueError("Invalid Discord status webhook URL")

        return config
    except FileNotFoundError:
        logger.error("Error: config.toml not found. Please create it.")
        raise
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise


