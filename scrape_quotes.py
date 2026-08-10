#!/usr/bin/env python3
"""quotes.toscrape.com/js から名言テキスト・著者名をPlaywrightで収集し、
Markdownとスクリーンショットとして保存する。"""

import logging
import random
import sys
import time
import urllib.robotparser
from datetime import date
from urllib.parse import urljoin

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

BASE_URL = "https://quotes.toscrape.com/"
START_PATH = "js/"
USER_AGENT = "python-automation-bot/1.0"
MIN_DELAY_SEC = 1
MAX_DELAY_SEC = 3
NAV_TIMEOUT_MS = 15000

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_robot_parser():
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(urljoin(BASE_URL, "robots.txt"))
    rp.read()
    return rp


def scrape():
    rp = load_robot_parser()
    quotes = []
    screenshot_path = f"quotes_{date.today().strftime('%Y%m%d')}.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(user_agent=USER_AGENT)
        page.set_default_navigation_timeout(NAV_TIMEOUT_MS)

        url = urljoin(BASE_URL, START_PATH)
        first_page = True

        while url:
            if not rp.can_fetch(USER_AGENT, url):
                logger.warning("robots.txtにより禁止されているためスキップします: %s", url)
                break

            logger.info("取得中: %s", url)
            try:
                page.goto(url, wait_until="networkidle")
            except PlaywrightError as exc:
                logger.error("接続エラーが発生しました: %s", exc)
                browser.close()
                sys.exit(1)

            if first_page:
                page.screenshot(path=screenshot_path, full_page=True)
                logger.info("スクリーンショットを %s に保存しました。", screenshot_path)
                first_page = False

            for quote_el in page.query_selector_all("div.quote"):
                text = quote_el.query_selector("span.text").inner_text()
                author = quote_el.query_selector("small.author").inner_text()
                quotes.append({"text": text, "author": author})

            next_el = page.query_selector("li.next a")
            next_href = next_el.get_attribute("href") if next_el else None
            url = urljoin(url, next_href) if next_href else None

            if url:
                time.sleep(random.uniform(MIN_DELAY_SEC, MAX_DELAY_SEC))

        browser.close()

    return quotes


def write_markdown(quotes):
    filename = f"quotes_{date.today().strftime('%Y%m%d')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Quotes to Scrape (JS) 収集結果\n\n")
        f.write(f"- 収集元: {urljoin(BASE_URL, START_PATH)}\n")
        f.write(f"- 収集日: {date.today().isoformat()}\n")
        f.write(f"- 収集件数: {len(quotes)}\n\n")
        f.write("| 名言 | 著者 |\n")
        f.write("| --- | --- |\n")
        for quote in quotes:
            text = quote["text"].replace("|", "\\|")
            author = quote["author"].replace("|", "\\|")
            f.write(f"| {text} | {author} |\n")
    logger.info("結果を %s に保存しました。", filename)
    return filename


def main():
    quotes = scrape()
    if not quotes:
        logger.error("名言情報を取得できませんでした。")
        sys.exit(1)
    write_markdown(quotes)


if __name__ == "__main__":
    main()
