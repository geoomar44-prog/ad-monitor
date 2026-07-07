#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ad Preview Monitor - GitHub Actions version
بياخد التوكن والـ Chat ID من الـ Secrets (environment variables)
"""

import os
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# توقيت السعودية/مصر في الرسائل (UTC+3)
TZ = timezone(timedelta(hours=3))

LOCATIONS = {
    "SA": 2682,  # السعودية
    "AE": 2784,  # الامارات
    "EG": 2818,  # مصر
    "KW": 2414,  # الكويت
    "QA": 2634,  # قطر
}

# ====== عدل الكيوردز من هنا ======
# (الكيورد, الدولة, اللغة, الجهاز)
# device: 30000 = mobile | 30001 = desktop
KEYWORDS = [
    ("كود خصم نون", "SA", "ar", 30000),
    ("عطور اجمل", "SA", "ar", 30000),
    ("trendyol كود خصم", "SA", "ar", 30000),
    ("نمشي خصم", "AE", "ar", 30000),
]
# =================================

SCREENSHOTS_DIR = Path("screenshots")
WAIT_AFTER_LOAD = 6
DELAY_BETWEEN_KEYWORDS = 8


def build_preview_url(keyword, country, lang, device):
    params = {"st": keyword, "loc": LOCATIONS[country], "hl": lang, "device": device}
    return "https://ads.google.com/anon/AdPreview?" + urllib.parse.urlencode(params)


def send_photo(image_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(image_path, "rb") as photo:
        r = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
            files={"photo": photo},
            timeout=60,
        )
    if not r.ok:
        print("Telegram error:", r.text)


def send_text(text):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=30,
    )


def run():
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    ts_file = datetime.now(TZ).strftime("%Y%m%d_%H%M")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            locale="ar",
            viewport={"width": 1366, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        for keyword, country, lang, device in KEYWORDS:
            url = build_preview_url(keyword, country, lang, device)
            device_name = "mobile" if device == 30000 else "desktop"
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
                time.sleep(WAIT_AFTER_LOAD)
                safe_kw = keyword.replace(" ", "_")[:30]
                shot = SCREENSHOTS_DIR / f"{ts_file}_{country}_{safe_kw}.png"
                page.screenshot(path=str(shot), full_page=True)
                send_photo(shot, f"🔍 {keyword}\n🌍 {country} | 📱 {device_name}\n🕐 {timestamp}")
                print(f"OK: {keyword}")
            except Exception as e:
                print(f"FAIL: {keyword}: {e}")
                try:
                    send_text(f"⚠️ فشل سكرين شوت: {keyword} ({country})\n{e}")
                except Exception:
                    pass
            time.sleep(DELAY_BETWEEN_KEYWORDS)

        browser.close()


if __name__ == "__main__":
    run()
