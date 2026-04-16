import csv
import re
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://news.itmo.ru/ru/"
NEWS_URL_RE = re.compile(r"^https://news\.itmo\.ru/ru/.+/(?:news|announce)/(\d+)/?$")


def create_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }
    )
    return session


SESSION = create_session()


def get_soup(url: str) -> BeautifulSoup:
    response = SESSION.get(url, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extract_news_links() -> List[str]:
    soup = get_soup(BASE_URL)
    links: Set[str] = set()

    for tag in soup.find_all("a", href=True):
        full_url = urljoin(BASE_URL, tag["href"])
        if NEWS_URL_RE.match(full_url):
            links.add(full_url)

    return sorted(links)


def extract_news_id(url: str) -> Optional[int]:
    match = NEWS_URL_RE.match(url)
    if match:
        return int(match.group(1))
    return None


def extract_title(page: BeautifulSoup) -> str:
    title_tag = page.find("h1")
    return title_tag.get_text(strip=True) if title_tag else "Без названия"


def extract_date(page: BeautifulSoup) -> str:
    text = page.get_text("\n", strip=True)
    match = re.search(r"\b\d{1,2}\s+[А-Яа-яЁё]+\s+\d{4}\b", text)
    return match.group(0) if match else "Дата не найдена"


def parse_news_page(url: str) -> Optional[Dict[str, str]]:
    news_id = extract_news_id(url)
    if news_id is None:
        return None

    page = get_soup(url)
    return {
        "id": str(news_id),
        "title": extract_title(page),
        "date": extract_date(page),
        "url": url,
    }


def save_to_csv(items: List[Dict[str, str]], filename: str = "news.csv") -> None:
    with open(filename, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=["id", "title", "date", "url"])
        writer.writeheader()
        writer.writerows(items)


def main() -> None:
    try:
        news_links = extract_news_links()
    except requests.RequestException as error:
        print(f"Не удалось получить список новостей: {error}")
        return

    result: List[Dict[str, str]] = []

    for url in news_links:
        try:
            item = parse_news_page(url)
            if item:
                result.append(item)
        except requests.RequestException as error:
            print(f"Ошибка при обработке {url}: {error}")

    save_to_csv(result)

    for item in result:
        print(item)

    print(f"\nСохранено записей: {len(result)}")


if __name__ == "__main__":
    main()
