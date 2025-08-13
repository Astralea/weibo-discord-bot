#!/usr/bin/env python3

import os
import sys
import json
import time
import base64
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager


def _ensure_outdir() -> Path:
    outdir = Path('weibo_captured')
    outdir.mkdir(exist_ok=True)
    return outdir


def create_chrome(headless: bool) -> webdriver.Chrome:
    options = ChromeOptions()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    # Enable performance logs so we can read Network.* events
    try:
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    except Exception:
        pass
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    except Exception:
        pass
    return driver


def create_firefox(headless: bool) -> webdriver.Firefox:
    options = FirefoxOptions()
    if headless:
        options.add_argument('--headless')
    options.set_preference('devtools.jsonview.enabled', False)
    service = FirefoxService(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    return driver


def extract_via_cdp(driver: webdriver.Chrome, page_url: str, url_substring: str, wait_seconds: int = 8) -> Optional[str]:
    try:
        # Must enable Network domain BEFORE navigation
        driver.execute_cdp_cmd('Network.enable', {})
    except Exception as e:
        print(f"CDP not available: {e}")
        return None

    driver.get(page_url)
    time.sleep(wait_seconds)

    request_id = None
    try:
        logs = driver.get_log('performance')
    except Exception as e:
        print(f"No performance logs: {e}")
        logs = []

    for entry in logs:
        try:
            msg = json.loads(entry.get('message', '{}')).get('message', {})
            if msg.get('method') == 'Network.responseReceived':
                resp = msg.get('params', {}).get('response', {})
                url = resp.get('url', '')
                status = resp.get('status')
                if url_substring in url and status == 200:
                    request_id = msg.get('params', {}).get('requestId')
                    break
        except Exception:
            continue

    if not request_id:
        print('Target AJAX response not found in logs. Consider increasing wait or refining url_substring.')
        return None

    try:
        body_obj = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
    except Exception as e:
        print(f"Network.getResponseBody failed: {e}")
        return None

    body = body_obj.get('body', '')
    if body_obj.get('base64Encoded'):
        try:
            body = base64.b64decode(body).decode('utf-8', errors='replace')
        except Exception:
            pass
    return body or None


def extract_via_async_fetch(driver: webdriver.Remote, page_url: str, fetch_url: str, wait_before_ms: int = 0) -> Optional[str]:
    driver.get(page_url)
    if wait_before_ms > 0:
        time.sleep(wait_before_ms / 1000.0)

    script = (
        "var done = arguments[0];\n"  # async callback
        "(async () => {\n"
        "  try {\n"
        "    const res = await fetch('" + fetch_url + "', { credentials: 'include', headers: { 'X-Requested-With': 'XMLHttpRequest' } });\n"
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
        print(f"fetch() error: {obj.get('error')}")
        return None

    return obj.get('text') or None


def save_json(text: str, dest_name: str) -> Path:
    outdir = _ensure_outdir()
    dest = outdir / dest_name
    with dest.open('w', encoding='utf-8') as f:
        f.write(text)
    return dest


def is_json_like(text: Optional[str]) -> bool:
    if not text:
        return False
    t = text.lstrip()
    return t.startswith('{') or t.startswith('[')


def main() -> int:
    # Settings
    uid = os.getenv('WEIBO_UID', '7618923072')
    headless = os.getenv('HEADLESS', '1') not in ('0', 'false', 'False')

    profile_url = f"https://weibo.com/u/{uid}"
    ajax_match = "/ajax/statuses/mymblog"  # substring to match in CDP logs
    ajax_url = f"/ajax/statuses/mymblog?uid={uid}&page=1&feature=0"  # relative for in-page fetch

    # Try Chrome + CDP first
    driver: Optional[webdriver.Remote] = None
    try:
        print(f"Starting Chrome (headless={headless}) for CDP test...")
        driver = create_chrome(headless=headless)
        body = extract_via_cdp(driver, profile_url, ajax_match, wait_seconds=10)
        if body and is_json_like(body):
            p = save_json(body, 'cdp_capture.json')
            print(f"SUCCESS [CDP]: Saved JSON to {p}")
            return 0
        else:
            print("CDP attempt did not yield JSON or body was not JSON-like.")
    except Exception as e:
        print(f"Chrome/CDP attempt failed: {e}")
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass

    # Fallback: Chrome or Firefox with in-page fetch
    for browser in ('chrome', 'firefox'):
        driver = None
        try:
            print(f"Starting {browser} (headless={headless}) for in-page fetch fallback...")
            if browser == 'chrome':
                driver = create_chrome(headless=headless)
            else:
                driver = create_firefox(headless=headless)

            text = extract_via_async_fetch(driver, profile_url, ajax_url, wait_before_ms=2500)
            if text and is_json_like(text):
                p = save_json(text, f'fetch_capture_{browser}.json')
                print(f"SUCCESS [fetch/{browser}]: Saved JSON to {p}")
                return 0
            else:
                print(f"fetch/{browser} did not return JSON from Weibo (possibly auth/cookie-gated).")
        except Exception as e:
            print(f"{browser} fetch attempt failed: {e}")
        finally:
            try:
                if driver:
                    driver.quit()
            except Exception:
                pass

    # As a last resort, prove the mechanism works against a public JSON endpoint (same-origin fetch)
    # Navigate to jsonplaceholder and fetch relative URL
    try:
        driver = create_chrome(headless=headless)
    except Exception:
        driver = create_firefox(headless=headless)

    try:
        print("Trying public JSON endpoint demo (jsonplaceholder.typicode.com)...")
        public_page = 'https://jsonplaceholder.typicode.com/'
        public_fetch = '/todos/1'
        text = extract_via_async_fetch(driver, public_page, public_fetch, wait_before_ms=0)
        if text and is_json_like(text):
            p = save_json(text, 'public_demo.json')
            print(f"SUCCESS [public demo]: Saved JSON to {p}")
            print("Note: Weibo may require valid cookies/XSRF; the technique works as shown above.")
            return 0
        else:
            print("Public demo failed to return JSON. Please check your network.")
            return 2
    except Exception as e:
        print(f"Public demo failed: {e}")
        return 2
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    sys.exit(main())