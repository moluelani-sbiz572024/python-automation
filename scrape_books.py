#!/usr/bin/env python3
"""books.toscrape.com から書籍タイトル・価格・在庫状況を収集し、Markdownで保存する。"""

import logging
import random
import sys
import time
import urllib.robotparser
from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
START_PATH = "catalogue/page-1.html"
USER_AGENT = "python-automation-bot/1.0"
MIN_DELAY_SEC = 1
MAX_DELAY_SEC = 3
REQUEST_TIMEOUT_SEC = 10

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_robot_parser():
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(urljoin(BASE_URL, "robots.txt"))
    rp.read()
    return rp


def fetch(session, rp, url):
    if not rp.can_fetch(USER_AGENT, url):
        logger.warning("robots.txtにより禁止されているためスキップします: %s", url)
        return None
    try:
        response = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SEC)
        response.raise_for_status()
        response.encoding = "utf-8"
    except requests.exceptions.RequestException as exc:
        logger.error("接続エラーが発生しました: %s", exc)
        sys.exit(1)
    return response.text


def parse_page(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    books = []
    for article in soup.select("article.product_pod"):
        title = article.h3.a["title"]
        price = article.select_one("p.price_color").get_text(strip=True)
        availability = article.select_one("p.instock.availability").get_text(strip=True)
        books.append({"title": title, "price": price, "availability": availability})

    next_link = soup.select_one("li.next a")
    next_url = urljoin(page_url, next_link["href"]) if next_link else None
    return books, next_url


def scrape():
    rp = load_robot_parser()
    session = requests.Session()
    all_books = []
    url = urljoin(BASE_URL, START_PATH)

    while url:
        logger.info("取得中: %s", url)
        html = fetch(session, rp, url)
        if html is None:
            break

        books, next_url = parse_page(html, url)
        all_books.extend(books)
        url = next_url
        if url:
            time.sleep(random.uniform(MIN_DELAY_SEC, MAX_DELAY_SEC))

    return all_books


def write_markdown(books):
    filename = f"books_{date.today().strftime('%Y%m%d')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Books to Scrape 収集結果\n\n")
        f.write(f"- 収集元: {BASE_URL}\n")
        f.write(f"- 収集日: {date.today().isoformat()}\n")
        f.write(f"- 収集件数: {len(books)}\n\n")
        f.write("| タイトル | 価格 | 在庫状況 |\n")
        f.write("| --- | --- | --- |\n")
        for book in books:
            title = book["title"].replace("|", "\\|")
            f.write(f"| {title} | {book['price']} | {book['availability']} |\n")
    logger.info("結果を %s に保存しました。", filename)
    return filename


def main():
    books = scrape()
    if not books:
        logger.error("書籍情報を取得できませんでした。")
        sys.exit(1)
    write_markdown(books)


if __name__ == "__main__":
    main()
