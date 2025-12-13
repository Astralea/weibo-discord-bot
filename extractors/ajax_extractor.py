from __future__ import annotations

import json
import re
import time
from typing import Optional, Dict, Any, List

from selenium import webdriver


def is_json_like(text: Optional[str]) -> bool:
    if not text:
        return False
    t = text.lstrip()
    return t.startswith('{') or t.startswith('[')


def extract_ajax_json(driver: webdriver.Remote, profile_url: str, uid: str, wait_before_ms: int = 1500) -> Optional[str]:
    """Navigate to mobile Weibo and fetch posts via mobile API.

    Weibo desktop AJAX API now requires login (returns 403).
    Mobile API at m.weibo.cn still works without authentication.

    Returns raw JSON string on success (None otherwise).
    """
    # Use mobile site instead of desktop
    mobile_url = f"https://m.weibo.cn/u/{uid}"
    driver.get(mobile_url)
    if wait_before_ms > 0:
        time.sleep(wait_before_ms / 1000.0)

    # Mobile API endpoint - containerid format is 107603 + uid
    container_id = f"107603{uid}"
    ajax_rel_url = f"/api/container/getIndex?containerid={container_id}"

    script = (
        "var done = arguments[0];\n"
        "(async () => {\n"
        "  try {\n"
        "    const res = await fetch('" + ajax_rel_url + "', { credentials: 'include' });\n"
        "    const text = await res.text();\n"
        "    done(JSON.stringify({ ok: true, status: res.status, text }));\n"
        "  } catch (e) {\n"
        "    done(JSON.stringify({ ok: false, error: String(e && e.message || e) }));\n"
        "  }\n"
        "})();\n"
    )

    raw = driver.execute_async_script(script)
    try:
        obj = json.loads(raw)
    except Exception:
        return None

    if not obj.get('ok'):
        return None

    text = obj.get('text') or ''
    return text if is_json_like(text) else None


def _convert_mobile_mblog_to_desktop_format(mblog: Dict[str, Any]) -> Dict[str, Any]:
    """Convert mobile API mblog format to match the desktop API format expected by the rest of the code."""
    result = mblog.copy()

    # Convert 'id' to integer (mobile API returns string, database requires int)
    if 'id' in result:
        try:
            result['id'] = int(result['id'])
        except (ValueError, TypeError):
            pass

    # Convert 'text' (HTML) to 'text_raw' (plain text) for compatibility
    text_html = mblog.get('text', '')
    # Remove HTML tags and convert <br /> to newlines
    text_raw = re.sub(r'<br\s*/?>', '\n', text_html)
    text_raw = re.sub(r'<[^>]+>', '', text_raw)
    result['text_raw'] = text_raw.strip()

    # Convert 'pics' array to 'pic_infos' dict format expected by downstream code
    pics = mblog.get('pics', [])
    if pics:
        pic_infos = {}
        pic_ids = []
        for pic in pics:
            pid = pic.get('pid', '')
            if pid:
                pic_ids.append(pid)
                # Build pic_infos entry matching desktop format
                pic_info = {}
                # Use 'large' if available, otherwise use main url
                if 'large' in pic and isinstance(pic['large'], dict):
                    large_url = pic['large'].get('url', pic.get('url', ''))
                    pic_info['large'] = {'url': large_url}
                    pic_info['bmiddle'] = {'url': pic.get('url', large_url)}
                else:
                    url = pic.get('url', '')
                    pic_info['large'] = {'url': url}
                    pic_info['bmiddle'] = {'url': url}
                pic_infos[pid] = pic_info
        result['pic_infos'] = pic_infos
        result['pic_ids'] = pic_ids

    # Handle retweeted_status recursively
    if 'retweeted_status' in result and isinstance(result['retweeted_status'], dict):
        result['retweeted_status'] = _convert_mobile_mblog_to_desktop_format(result['retweeted_status'])

    # Ensure idstr/mid are set for URL generation
    if 'idstr' not in result and 'id' in result:
        result['idstr'] = str(result['id'])
    if 'mid' not in result and 'id' in result:
        result['mid'] = str(result['id'])

    return result


def to_list_from_ajax_json(raw: str) -> Optional[List[Dict[str, Any]]]:
    """Parse mobile API JSON response into a list of post objects."""
    try:
        data = json.loads(raw)
    except Exception:
        return None

    # Desktop format: data.list[]
    if isinstance(data, dict) and isinstance(data.get('data'), dict):
        # Try desktop format first
        if isinstance(data['data'].get('list'), list):
            return data['data']['list']

        # Mobile format: data.cards[].mblog
        if isinstance(data['data'].get('cards'), list):
            posts = []
            for card in data['data']['cards']:
                if isinstance(card, dict) and 'mblog' in card:
                    mblog = card['mblog']
                    if isinstance(mblog, dict):
                        # Convert mobile format to desktop format for compatibility
                        converted = _convert_mobile_mblog_to_desktop_format(mblog)
                        posts.append(converted)
            return posts if posts else None

    return None



