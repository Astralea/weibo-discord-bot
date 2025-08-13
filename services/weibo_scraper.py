from __future__ import annotations

import json
import logging
import random
import time
import uuid
from datetime import datetime, timedelta
import os
import platform
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

import pytz
import schedule
from discord_webhook import DiscordWebhook, DiscordEmbed
from core.media.image_collage import combine_images, resize_gif
from PIL import Image

from core.webdriver_manager import WebDriverManager
from core.database import DatabaseManager
from core.image_manager import ImageManager
from core.rate_limiter import RateLimiter
from core import settings
from extractors.ajax_extractor import extract_ajax_json, to_list_from_ajax_json
from extractors.mobile_dom_extractor import extract_mobile_dom_as_list


logger = logging.getLogger(__name__)

from core.settings import EXTRACTION_METHOD


class WeiboScraper:
    def __init__(self, config: Dict[str, Any], account_names: List[str] = 'auto'):
        self.config = config
        self.driver = WebDriverManager.create_driver(headless=True)
        self.db_manager = DatabaseManager()
        self.image_manager = ImageManager(Path(__file__).resolve().parent.parent / 'images')
        self.rate_limiter = RateLimiter(max_requests=settings.RATE_LIMIT_MAX_REQUESTS, time_window=settings.RATE_LIMIT_TIME_WINDOW)
        self.kawaii_emojis = ["(✿ ♥‿♥)", "(｡♥‿♥｡)"]
        self.kawaii_texts = ["ぴーかぴかに動いてるよ！", "全システム、ばっちりだよ！"]
        self.kawaii_titles = ["ぴょんぴょんアップデート！🐰", "ちゅるちゅるスクリプト！🍜"]

        # Optional kawaii content
        try:
            self._load_kawaii_content()
        except Exception:
            pass

        if account_names == 'auto':
            self.account_names = list(self.config['weibo'].keys())
        else:
            self.account_names = account_names
        logger.info(f"WeiboScraper initialized with {len(self.account_names)} accounts")

    def _is_driver_alive(self) -> bool:
        try:
            self.driver.current_url
            return True
        except Exception:
            return False

    def _recreate_driver(self):
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        self.driver = WebDriverManager.create_driver()

    def _extract_uid_from_url(self, url: str) -> Optional[str]:
        import re
        m = re.search(r'/u/([0-9]+)', url)
        if m:
            return m.group(1)
        m = re.search(r'weibo\.com/([0-9]+)(?:\?|$|/)', url)
        if m:
            return m.group(1)
        return None

    def get_weibo_content_once(self, endpoints: Dict[str, str]) -> Optional[List[Dict[str, Any]]]:
        self.rate_limiter.wait_if_needed()
        if not self._is_driver_alive():
            self._recreate_driver()

        main_url = endpoints['read_link_url']
        method = EXTRACTION_METHOD

        if method == 'ajax_json':
            uid = self._extract_uid_from_url(main_url)
            if not uid:
                self.driver.get(main_url)
                time.sleep(2)
                try:
                    val = self.driver.execute_script("return (window.$CONFIG && $CONFIG.uid) || (window.CONFIG && window.CONFIG.uid) || '';")
                    if val and str(val).isdigit():
                        uid = str(val)
                except Exception:
                    pass
            if not uid:
                logger.error('Cannot derive uid from read_link_url for ajax_json method')
                return None

            # Always use canonical profile URL like the test script
            profile_url = f"https://weibo.com/u/{uid}"
            raw = extract_ajax_json(self.driver, profile_url, uid, wait_before_ms=settings.AJAX_WAIT_MS)
            if not raw or not raw.strip():
                logger.error('AJAX capture returned empty or no JSON')
                return None
            try:
                out_dir = Path('weibo_tmp')
                out_dir.mkdir(exist_ok=True)
                account_name = endpoints.get('account_name') or f"uid{uid}"
                # sanitize account name for filesystem safety
                safe_name = re.sub(r'[^A-Za-z0-9._-]+', '_', str(account_name))
                tz_gmt8 = pytz.timezone('Asia/Shanghai')
                timestamp = datetime.now(tz_gmt8).strftime('%Y%m%d_%H%M%S')
                out_path = out_dir / f"{safe_name}_{timestamp}.json"
                out_path.write_text(raw, encoding='utf-8')
                logger.info(f'Captured JSON saved to {out_path}')
            except Exception as e:
                logger.warning(f'Failed to save captured JSON: {e}')
            lst = to_list_from_ajax_json(raw)
            if not lst:
                logger.error('AJAX JSON could not be parsed into list')
                return None
            return lst

        if method == 'mobile_dom':
            uid = self._extract_uid_from_url(main_url)
            if not uid:
                logger.error('Cannot derive uid from read_link_url for mobile_dom method')
                return None
            mobile_url = f'https://m.weibo.cn/u/{uid}'
            return extract_mobile_dom_as_list(self.driver, mobile_url, max_scrolls=8)

        logger.error(f'Unknown extraction method: {method}')
        return None

    def get_weibo_content_loop(self, endpoints: Dict[str, str]) -> Optional[List[Dict[str, Any]]]:
        max_retries = 10
        retry_count = 0
        logger.info(f'Getting Weibo content... @ {datetime.now()}')
        while retry_count < max_retries:
            content = self.get_weibo_content_once(endpoints)
            if content:
                logger.info(f'Successfully retrieved {len(content)} posts')
                return content
            retry_count += 1
            logger.warning(f'Retrying... ({retry_count}/{max_retries})')
            time.sleep(90)
        logger.error('Failed to get content after maximum retries')
        return None

    def scan(self, endpoints: Dict[str, str]):
        content = self.get_weibo_content_loop(endpoints)
        if not content:
            logger.warning('Failed to get content')
            return
        processed_count = 0
        for item in reversed(content):
            try:
                if self.db_manager.check_and_add_id(item['id']):
                    self.parse_item(item, endpoints)
                    processed_count += 1
                    time.sleep(10)
            except Exception as e:
                logger.error(f"Error processing item {item.get('id', 'unknown')}: {e}")
        if processed_count > 0:
            logger.info(f'Processed {processed_count} new posts')

    def create_webhook_instance(self, endpoints: Dict[str, str], **kwargs) -> DiscordWebhook:
        webhook_url = endpoints.get('message_webhook')
        if not webhook_url or not webhook_url.startswith('https://discord.com/api/webhooks/'):
            raise ValueError('Invalid Discord webhook URL')
        avatar_url = endpoints.get('avatar_url')
        return DiscordWebhook(url=webhook_url, avatar_url=avatar_url, **kwargs)

    def _load_kawaii_content(self):
        try:
            with open('kawaii_content.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.kawaii_emojis = data.get('kawaii_emojis', self.kawaii_emojis)
            self.kawaii_texts = data.get('kawaii_texts', self.kawaii_texts)
            self.kawaii_titles = data.get('kawaii_titles', self.kawaii_titles)
        except Exception:
            pass

    def _create_base_embed(self, item: Dict[str, Any], endpoints: Dict[str, str]) -> DiscordEmbed:
        import re
        text_raw = item.get('text_raw', '')
        created_at = item.get('created_at', '')
        title = endpoints.get('title', 'Weibo Post')
        source = item.get('source', 'Unknown')
        embed_color = 16738740
        s = str(created_at).strip()
        now = datetime.now()
        dt = None
        try:
            from datetime import datetime as _dt
            dt = _dt.strptime(s, '%a %b %d %H:%M:%S %z %Y')
        except Exception:
            dt = None
        if dt is None:
            m = __import__('re').match(r'^(\d{1,2})-(\d{1,2}) (\d{1,2}):(\d{2})$', s)
            if m:
                month, day, hh, mm = map(int, m.groups())
                dt = now.replace(month=month, day=day, hour=hh, minute=mm, second=0, microsecond=0)
        if dt is None:
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    dt = datetime.strptime(s, fmt)
                    break
                except Exception:
                    pass
        if dt is None:
            m = re.match(r'^昨天\s+(\d{1,2}):(\d{2})$', s)
            if m:
                hh, mm = map(int, m.groups())
                dt = (now.replace(hour=hh, minute=mm, second=0, microsecond=0))
                dt = dt.replace(day=now.day) - timedelta(days=1)
            else:
                m = re.match(r'^今天\s+(\d{1,2}):(\d{2})$', s)
                if m:
                    hh, mm = map(int, m.groups())
                    dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if dt is None:
            dt = now
        discord_timestamp = dt.timestamp()
        # Always use desktop detail URL for the post
        post_url = endpoints.get('read_link_url', '')
        try:
            idstr = str(item.get('idstr') or item.get('mid') or item.get('id') or '').strip()
            post_url = f"https://weibo.com/detail/{idstr}"
        except Exception:
            pass
        embed = DiscordEmbed(title=title, description=text_raw, color=embed_color, url=post_url)
        embed.set_footer(text=f"来自 {source}")
        try:
            embed.set_timestamp(discord_timestamp)
        except Exception:
            embed.set_timestamp()
        return embed

    def parse_item_text_only(self, item: Dict[str, Any], embed: DiscordEmbed, endpoints: Dict[str, str]) -> int:
        webhook_message = self.create_webhook_instance(endpoints)
        webhook_message.add_embed(embed)
        response = webhook_message.execute()
        return response.status_code

    def parse_item(self, item: Dict[str, Any], endpoints: Dict[str, str]) -> int:
        embed = self._create_base_embed(item, endpoints)
        if 'retweeted_status' in item:
            return self.parse_item_retweet(item, embed, endpoints)
        if 'pic_infos' in item:
            return self.parse_item_with_images(item, embed, endpoints)
        if 'page_info' in item:
            if 'media_info' in item['page_info']:
                return self.parse_item_with_video(item, embed, endpoints)
            if 'page_pic' in item['page_info']:
                return self.parse_item_with_page_pic(item, embed, endpoints)
            debug_file = f'debug_{str(uuid.uuid4())[-10:]}.json'
            Path(debug_file).write_text(json.dumps(item, indent=2, ensure_ascii=False), encoding='utf-8')
            logger.warning(f'Unknown page_info structure logged to {debug_file}')
            return self.parse_item_text_only(item, embed, endpoints)
        return self.parse_item_text_only(item, embed, endpoints)

    def start(self):
        logger.info("Starting Weibo scraper...")
        try:
            for account in self.account_names:
                try:
                    endpoints = self.config['weibo'][account].copy()
                    endpoints['account_name'] = account
                    self.scan(endpoints)
                except Exception as e:
                    logger.error(f"Error scanning account {account}: {e}")
            schedule.every(15).minutes.do(self._scan_all_accounts)
            schedule.every(6).hours.do(self.send_status, self.config['status']['message_webhook'])
            schedule.every(24).hours.do(self._cleanup_old_data)
            self.send_status(self.config['status']['message_webhook'])
            logger.info("Scraper started. Press Ctrl+C to stop.")
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nStopping scraper...")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")

    def _scan_all_accounts(self):
        for account in self.account_names:
            try:
                endpoints = self.config['weibo'][account].copy()
                endpoints['account_name'] = account
                self.scan(endpoints)
            except Exception as e:
                logger.error(f"Error scanning account {account}: {e}")

    def _cleanup_old_data(self):
        try:
            if self.db_manager:
                self.db_manager.cleanup_old_records(days=30)
            if self.image_manager:
                self.image_manager.cleanup_all()
            logger.info("Periodic cleanup completed")
        except Exception as e:
            logger.error(f"Error during periodic cleanup: {e}")

    def cleanup(self):
        logger.info("Starting cleanup...")
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
                logger.info("WebDriver closed")
        except Exception as e:
            logger.error(f"Error closing webdriver: {e}")
        try:
            if hasattr(self, 'db_manager') and self.db_manager:
                self.db_manager.close()
        except Exception as e:
            logger.error(f"Error closing database: {e}")
        try:
            if hasattr(self, 'image_manager') and self.image_manager:
                self.image_manager.cleanup_all()
        except Exception as e:
            logger.error(f"Error cleaning up images: {e}")
        logger.info("Cleanup completed.")

    def send_status(self, status_webhook_url: str) -> int:
        try:
            webhook_status = DiscordWebhook(url=status_webhook_url)
            embed_color = 16738740
            emoji = random.choice(self.kawaii_emojis)
            text = random.choice(self.kawaii_texts)
            title = random.choice(self.kawaii_titles)
            if platform.system() == 'Windows':
                machine_info = f"{platform.node()} {platform.machine()}"
            else:
                machine_info = f"{os.uname().nodename} {os.uname().machine}"
            timezone = pytz.timezone('Etc/GMT-9')
            time_now = datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
            embed = DiscordEmbed(title=title, description=f"{emoji} {text} @ {time_now} -- {machine_info}", color=embed_color)
            embed.set_timestamp()
            webhook_status.add_embed(embed)
            response = webhook_status.execute()
            return response.status_code
        except Exception as e:
            logger.error(f"Error sending status: {e}")
            return 500


    def parse_item_with_page_pic(self, item: Dict[str, Any], embed: DiscordEmbed, endpoints: Dict[str, str]) -> int:
        try:
            page_info = item.get('page_info') or {}
            page_pic = page_info.get('page_pic')
            if isinstance(page_pic, dict):
                image_url = page_pic.get('url') or page_pic.get('pic')
            else:
                image_url = page_pic
            if not image_url:
                return self.parse_item_text_only(item, embed, endpoints)
            image_path = self.image_manager.download_image(image_url)
            if image_path:
                webhook_message = self.create_webhook_instance(endpoints)
                with image_path.open('rb') as f:
                    webhook_message.add_file(file=f.read(), filename=image_path.name)
                embed.set_image(url=f'attachment://{image_path.name}')
                webhook_message.add_embed(embed)
                response = webhook_message.execute()
                if self.image_manager.should_delete_images:
                    self.image_manager.delete_images([image_path])
                return response.status_code
            else:
                return self.parse_item_text_only(item, embed, endpoints)
        except Exception as e:
            logger.error(f"Error processing page pic: {e}")
            return self.parse_item_text_only(item, embed, endpoints)

    def parse_item_with_images(self, item: Dict[str, Any], embed: DiscordEmbed, endpoints: Dict[str, str]) -> int:
        try:
            image_urls: List[str] = []
            for _, v in (item.get('pic_infos') or {}).items():
                if not isinstance(v, dict):
                    continue
                if 'bmiddle' in v and isinstance(v['bmiddle'], dict) and v['bmiddle'].get('url'):
                    image_urls.append(v['bmiddle']['url'])
                elif 'large' in v and isinstance(v['large'], dict) and v['large'].get('url'):
                    image_urls.append(v['large']['url'])
                elif 'mw1024' in v and isinstance(v['mw1024'], dict) and v['mw1024'].get('url'):
                    image_urls.append(v['mw1024']['url'])
                elif 'mw690' in v and isinstance(v['mw690'], dict) and v['mw690'].get('url'):
                    image_urls.append(v['mw690']['url'])
                elif 'mw480' in v and isinstance(v['mw480'], dict) and v['mw480'].get('url'):
                    image_urls.append(v['mw480']['url'])
                elif 'original' in v and isinstance(v['original'], dict) and v['original'].get('url'):
                    image_urls.append(v['original']['url'])
            image_paths = self.image_manager.download_images(image_urls)
            if not image_paths:
                return self.parse_item_text_only(item, embed, endpoints)
            compressed_paths: List[Path] = []
            for image_path in image_paths:
                compressed_paths.append(self.compress_image(image_path, max_size_mb=settings.DISCORD_ATTACHMENT_MAX_MB))
            if len(compressed_paths) == 1:
                collage_path = compressed_paths[0]
            else:
                try:
                    collage_path = combine_images(compressed_paths)
                except Exception as e:
                    logger.error(f"Error creating image collage: {e}")
                    return self.parse_item_text_only(item, embed, endpoints)
            try:
                file_size_mb = collage_path.stat().st_size / (1024 ** 2)
                if file_size_mb > settings.DISCORD_ATTACHMENT_MAX_MB:
                    logger.warning(f"Image collage too large ({file_size_mb:.1f}MB), sending text-only")
                    return self.parse_item_text_only(item, embed, endpoints)
            except Exception as e:
                logger.error(f"Error checking file size: {e}")
                return self.parse_item_text_only(item, embed, endpoints)
            webhook_message = self.create_webhook_instance(endpoints)
            with collage_path.open("rb") as f:
                webhook_message.add_file(file=f.read(), filename=collage_path.name)
            embed.set_image(url=f'attachment://{collage_path.name}')
            webhook_message.add_embed(embed)
            response = webhook_message.execute()
            if len(image_paths) > 1:
                try:
                    time.sleep(1)
                    self.send_animated_images(image_paths, endpoints)
                except Exception:
                    pass
            if self.image_manager.should_delete_images and compressed_paths:
                self.image_manager.delete_images(compressed_paths)
                if collage_path and collage_path not in compressed_paths:
                    self.image_manager.delete_images([collage_path])
            return response.status_code
        except Exception as e:
            logger.error(f"Error processing images: {e}")
            return self.parse_item_text_only(item, embed, endpoints)

    def send_animated_images(self, image_paths: List[Path], endpoints: Dict[str, str]) -> int:
        try:
            gif_webhook = self.create_webhook_instance(endpoints)
            files_to_delete: List[Path] = []
            for image_path in image_paths:
                if image_path.suffix.lower() == ".gif":
                    file_size_mb = image_path.stat().st_size / (1024 ** 2)
                    while file_size_mb > settings.DISCORD_ATTACHMENT_MAX_MB:
                        try:
                            image_path = resize_gif(image_path)
                            files_to_delete.append(image_path)
                            file_size_mb = image_path.stat().st_size / (1024 ** 2)
                        except Exception as e:
                            logger.error(f"Error resizing GIF {image_path}: {e}")
                            break
                    if file_size_mb <= 3:
                        with image_path.open("rb") as f:
                            gif_webhook.add_file(file=f.read(), filename=image_path.name)
            if getattr(gif_webhook, 'files', None):
                response = gif_webhook.execute()
                if self.image_manager.should_delete_images:
                    self.image_manager.delete_images(files_to_delete)
                return response.status_code
            return 204
        except Exception as e:
            logger.error(f"Error in send_animated_images: {e}")
            return 500

    def parse_item_with_video(self, item: Dict[str, Any], embed: DiscordEmbed, endpoints: Dict[str, str]) -> int:
        try:
            # Do not send the separate video URL to Discord due to Weibo restrictions.
            # Only send the embed (with per-post URL) so users can click through.
            webhook_message = self.create_webhook_instance(endpoints)
            webhook_message.add_embed(embed)
            response = webhook_message.execute()
            return response.status_code
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return self.parse_item_text_only(item, embed, endpoints)

    def parse_item_retweet(self, item: Dict[str, Any], embed: DiscordEmbed, endpoints: Dict[str, str]) -> int:
        try:
            retweeted_status = item.get('retweeted_status') or {}
            retweet_text = retweeted_status.get('text_raw') or retweeted_status.get('text') or ''
            user_name = ((retweeted_status.get('user') or {}).get('screen_name')) or '转发'
            image_paths: List[Path] = []
            collage_path: Optional[Path] = None
            if 'pic_infos' in retweeted_status:
                image_urls: List[str] = []
                for _, v in (retweeted_status.get('pic_infos') or {}).items():
                    if not isinstance(v, dict):
                        continue
                    if 'bmiddle' in v and isinstance(v['bmiddle'], dict) and v['bmiddle'].get('url'):
                        image_urls.append(v['bmiddle']['url'])
                    elif 'large' in v and isinstance(v['large'], dict) and v['large'].get('url'):
                        image_urls.append(v['large']['url'])
                    elif 'mw1024' in v and isinstance(v['mw1024'], dict) and v['mw1024'].get('url'):
                        image_urls.append(v['mw1024']['url'])
                    elif 'mw690' in v and isinstance(v['mw690'], dict) and v['mw690'].get('url'):
                        image_urls.append(v['mw690']['url'])
                    elif 'mw480' in v and isinstance(v['mw480'], dict) and v['mw480'].get('url'):
                        image_urls.append(v['mw480']['url'])
                    elif 'original' in v and isinstance(v['original'], dict) and v['original'].get('url'):
                        image_urls.append(v['original']['url'])
                image_paths = self.image_manager.download_images(image_urls)
                compressed_paths: List[Path] = []
                for image_path in image_paths:
                    compressed_paths.append(self.compress_image(image_path, max_size_mb=3.0))
                if len(compressed_paths) == 1:
                    collage_path = compressed_paths[0]
                elif len(compressed_paths) > 1:
                    try:
                        collage_path = combine_images(compressed_paths)
                    except Exception as e:
                        logger.error(f"Error creating retweet image collage: {e}")
                        collage_path = None
            if collage_path:
                try:
                    file_size_mb = collage_path.stat().st_size / (1024 ** 2)
                    if file_size_mb <= 3:
                        webhook_message = self.create_webhook_instance(endpoints)
                        with collage_path.open("rb") as f:
                            webhook_message.add_file(file=f.read(), filename=collage_path.name)
                        embed.set_image(url=f'attachment://{collage_path.name}')
                    else:
                        logger.warning(f"Retweet image too large ({file_size_mb:.1f}MB), sending without image")
                        webhook_message = self.create_webhook_instance(endpoints)
                except Exception as e:
                    logger.error(f"Error processing retweet image: {e}")
                    webhook_message = self.create_webhook_instance(endpoints)
            else:
                webhook_message = self.create_webhook_instance(endpoints)
            embed.add_embed_field(name=f"@{user_name}", value=retweet_text)
            webhook_message.add_embed(embed)
            try:
                response = webhook_message.execute()
                if self.image_manager.should_delete_images and image_paths:
                    self.image_manager.delete_images(image_paths)
                    if collage_path and collage_path not in image_paths:
                        self.image_manager.delete_images([collage_path])
                return response.status_code
            except Exception as e:
                logger.error(f"Error sending retweet: {e}")
                return 500
        except Exception as e:
            logger.error(f"Error processing retweet: {e}")
            return self.parse_item_text_only(item, embed, endpoints)

    def compress_image(self, image_path: Path, max_size_mb: float = 5.0) -> Path:
        try:
            file_size_mb = image_path.stat().st_size / (1024 ** 2)
            if file_size_mb <= max_size_mb:
                return image_path
            logger.info(f"Compressing {image_path.name} from {file_size_mb:.1f}MB")
            with Image.open(image_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                original_width, original_height = img.size
                max_dimension = 1024
                if original_width > max_dimension or original_height > max_dimension:
                    scale_factor = min(max_dimension / original_width, max_dimension / original_height)
                    new_width = int(original_width * scale_factor)
                    new_height = int(original_height * scale_factor)
                    new_width = min(new_width, max_dimension)
                    new_height = min(new_height, max_dimension)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                quality = 70
                compression_attempts = 0
                max_attempts = 10
                while file_size_mb > max_size_mb and compression_attempts < max_attempts:
                    compression_attempts += 1
                    compressed_path = image_path.parent / f"compressed_{image_path.name}"
                    img.save(compressed_path, 'JPEG', quality=quality, optimize=True)
                    new_size_mb = compressed_path.stat().st_size / (1024 ** 2)
                    if new_size_mb <= max_size_mb:
                        image_path.unlink()
                        compressed_path.rename(image_path)
                        return image_path
                    else:
                        quality = max(10, quality - 15)
                        compressed_path.unlink()
                if file_size_mb > max_size_mb:
                    target_pixels = int((max_size_mb * 1024 * 1024) / 3)
                    current_pixels = img.width * img.height
                    if current_pixels > target_pixels:
                        scale_factor = (target_pixels / current_pixels) ** 0.5
                        new_width = max(100, int(img.width * scale_factor))
                        new_height = max(100, int(img.height * scale_factor))
                        new_width = min(new_width, max_dimension)
                        new_height = min(new_height, max_dimension)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        img.save(image_path, 'JPEG', quality=40, optimize=True)
                return image_path
        except Exception as e:
            logger.error(f"Error compressing image {image_path}: {e}")
            return image_path


