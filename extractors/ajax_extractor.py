from __future__ import annotations

import json
import time
from typing import Optional, Dict, Any, List

from selenium import webdriver


def is_json_like(text: Optional[str]) -> bool:
    if not text:
        return False
    t = text.lstrip()
    return t.startswith('{') or t.startswith('[')


def extract_ajax_json(driver: webdriver.Remote, profile_url: str, uid: str, wait_before_ms: int = 1500) -> Optional[str]:
    """Navigate to desktop profile_url, then fetch AJAX JSON in-page with credentials included.

    Returns raw JSON string on success (None otherwise).
    """
    driver.get(profile_url)
    if wait_before_ms > 0:
        time.sleep(wait_before_ms / 1000.0)

    ajax_rel_url = f"/ajax/statuses/mymblog?uid={uid}&page=1&feature=0"
    script = (
        "var done = arguments[0];\n"
        "(async () => {\n"
        "  try {\n"
        "    const m = document.cookie.match(/(?:^|;\\s*)XSRF-TOKEN=([^;]+)/);\n"
        "    const xsrf = m ? decodeURIComponent(m[1]) : null;\n"
        "    const headers = { 'X-Requested-With': 'XMLHttpRequest' };\n"
        "    if (xsrf) headers['X-XSRF-TOKEN'] = xsrf;\n"
        "    const res = await fetch('" + ajax_rel_url + "', { credentials: 'include', headers });\n"
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


def to_list_from_ajax_json(raw: str) -> Optional[List[Dict[str, Any]]]:
    try:
        data = json.loads(raw)
    except Exception:
        return None
    if isinstance(data, dict) and isinstance(data.get('data'), dict) and isinstance(data['data'].get('list'), list):
        return data['data']['list']
    return None



