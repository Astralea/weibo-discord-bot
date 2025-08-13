from __future__ import annotations

import uuid
import logging
from pathlib import Path
from typing import List, Optional

import requests
from core import settings


logger = logging.getLogger(__name__)


class ImageManager:
    def __init__(self, image_dir: Path):
        if not isinstance(image_dir, Path):
            image_dir = Path(image_dir)
        image_dir = image_dir.resolve()
        if not str(image_dir).startswith(str(Path.cwd().resolve())):
            raise ValueError('Image directory must be within current working directory')
        self.image_dir = image_dir
        self.image_dir.mkdir(exist_ok=True)
        self.should_delete_images = True
        self.downloaded_files = set()
        logger.info(f'Image manager initialized: {self.image_dir}')

    def _validate_url(self, url: str) -> bool:
        if not isinstance(url, str) or not url.strip():
            return False
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.scheme != 'https':
                return False
            valid_domains = ['wx1.sinaimg.cn', 'wx2.sinaimg.cn', 'wx3.sinaimg.cn', 'wx4.sinaimg.cn', 'sinaimg.cn', 'weibo.com', 'weibo.cn']
            if not any(domain in parsed.netloc for domain in valid_domains):
                return False
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            if not any(parsed.path.lower().endswith(ext) for ext in valid_extensions):
                return False
            return True
        except Exception:
            return False

    def download_image(self, url: str) -> Optional[Path]:
        try:
            if not self._validate_url(url):
                logger.warning(f'Invalid or unsafe URL: {url}')
                return None
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://weibo.com/',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site',
            }
            response = requests.get(url, headers=headers, timeout=settings.REQUEST_TIMEOUT_SECONDS, stream=True)
            if response.status_code != 200:
                logger.warning(f'HTTP {response.status_code} for URL: {url}')
                return None
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                logger.warning(f'Invalid content type: {content_type} for URL: {url}')
                return None
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > settings.IMAGE_MAX_DOWNLOAD_BYTES:
                logger.warning(f'File too large: {content_length} bytes for URL: {url}')
                return None
            file_extension = Path(url).suffix or '.jpg'
            file_name = f"{uuid.uuid4()}{file_extension}"
            file_path = self.image_dir / file_name
            downloaded_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        downloaded_size += len(chunk)
                        if downloaded_size > settings.IMAGE_MAX_DOWNLOAD_BYTES:
                            f.close()
                            file_path.unlink(missing_ok=True)
                            logger.warning(f'File exceeded size limit during download: {url}')
                            return None
                        f.write(chunk)
            self.downloaded_files.add(file_path)
            logger.debug(f'Downloaded image: {file_path.name} ({downloaded_size} bytes)')
            return file_path
        except requests.RequestException as e:
            logger.error(f'Request error downloading image {url}: {e}')
            return None
        except Exception as e:
            logger.error(f'Error downloading image {url}: {e}')
            return None

    def download_images(self, urls: List[str]) -> List[Path]:
        downloaded_images = []
        for url in urls:
            if not isinstance(url, str):
                logger.warning(f'Invalid URL type: {type(url)}')
                continue
            image_path = self.download_image(url)
            if image_path:
                downloaded_images.append(image_path)
        logger.info(f'Downloaded {len(downloaded_images)}/{len(urls)} images')
        return downloaded_images

    def delete_images(self, file_paths: List[Path]):
        deleted_count = 0
        for file_path in file_paths:
            try:
                path = Path(file_path)
                if not str(path.resolve()).startswith(str(self.image_dir.resolve())):
                    logger.warning(f'Attempted to delete file outside image directory: {path}')
                    continue
                if path.exists():
                    path.unlink()
                    deleted_count += 1
                    if path in self.downloaded_files:
                        self.downloaded_files.remove(path)
            except Exception as e:
                logger.error(f'Error deleting file {file_path}: {e}')
        if deleted_count > 0:
            logger.debug(f'Deleted {deleted_count} image files')

    def cleanup_all(self):
        try:
            for file_path in list(self.downloaded_files):
                try:
                    if file_path.exists():
                        file_path.unlink()
                except Exception as e:
                    logger.error(f'Error cleaning up {file_path}: {e}')
            self.downloaded_files.clear()
            logger.info('Cleaned up all downloaded images')
        except Exception as e:
            logger.error(f'Error during cleanup: {e}')


