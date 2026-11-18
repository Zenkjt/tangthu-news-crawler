from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from tangthu_crawler.discovery import SourceDiscovery
from tangthu_crawler.extractor import ArticleExtractor


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi,en-US;q=0.8,en;q=0.6",
    "Referer": "https://vnexpress.net/",
}

SOURCE_BASE = {
    "id": "vnexpress-live-smoke",
    "name": "VnExpress live smoke test",
    "site_adapter": "vnexpress",
    "discovery": ["html"],
    "html": {
        "strategy": "page_articles",
        "max_articles": 5,
        "max_pages": 3,
        "article_container_selectors": ["#paging"],
        "article_link_selectors": [
            "article.item-news h3.title-news a",
            "article.item-news h2.title-news a",
        ],
        "next_page_selectors": [
            'a[rel~="next"]',
            ".pagination a.next",
            "a.btn-next",
        ],
        "excluded_path_prefixes": [
            "/tag/", "/topic/", "/search/", "/tim-kiem/", "/category/",
            "/photo/", "/podcast/", "/live/", "/infographics/", "/video/",
            "/chu-de/", "/tac-gia/", "/author/",
        ],
    },
    "extractor": {"engine": "vnexpress"},
    "quality_gate": {
        "enabled": True,
        "require_title": True,
        "min_body_chars": 300,
        "min_paragraphs": 2,
        "reject_titles": ["Untitled", "Article"],
    },
    "http": {"headers": {"Referer": "https://vnexpress.net/"}},
}


def valid_topic_url(value: str) -> bool:
    parsed = urlparse(value)
    return (
        parsed.scheme in {"http", "https"}
        and parsed.hostname in {"vnexpress.net", "www.vnexpress.net"}
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--max-articles", type=int, default=5)
    parser.add_argument("--max-pages", type=int, default=3)
    args = parser.parse_args()

    if not valid_topic_url(args.url):
        print("ERROR: URL must use vnexpress.net or www.vnexpress.net")
        return 2

    source = dict(SOURCE_BASE)
    source["url"] = args.url
    source["html"] = dict(SOURCE_BASE["html"])
    source["html"]["max_articles"] = max(1, min(args.max_articles, 100))
    source["html"]["max_pages"] = max(1, min(args.max_pages, 5))

    settings = {"crawler": {"request_timeout": 25}}
    print(f"SMOKE_SOURCE={args.url}")
    print(
        "LIMITS="
        f"max_articles:{source['html']['max_articles']},"
        f"max_pages:{source['html']['max_pages']}"
    )

    discovery = SourceDiscovery(source, settings)
    discovery.session.headers.update(DEFAULT_HEADERS)
    refs = discovery.discover()

    print(f"DISCOVERED_COUNT={len(refs)}")
    for index, ref in enumerate(refs, start=1):
        print(f"DISCOVERED[{index}]={ref.url}")

    if not refs:
        print("RESULT=FAIL: discovery returned zero article URLs")
        return 1

    extractor = ArticleExtractor()
    passed = 0
    failed = 0
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    with tempfile.TemporaryDirectory(prefix="vnexpress-smoke-") as temp_dir:
        temp_path = Path(temp_dir)

        for index, ref in enumerate(refs, start=1):
            try:
                response = session.get(ref.url, timeout=25, allow_redirects=True)
                response.raise_for_status()

                final_host = (urlparse(response.url).hostname or "").lower()
                if final_host not in {"vnexpress.net", "www.vnexpress.net"}:
                    raise ValueError(f"article redirected outside VnExpress: {response.url}")

                html_path = temp_path / f"article-{index}.html"
                html_path.write_text(response.text, encoding="utf-8")

                article = extractor.extract(html_path, ref.url, source)
                ok, reason = extractor.quality_check(article, source)

                title = (article.get("title") or "").strip()
                body = (article.get("body") or "").strip()
                paragraphs = len(ArticleExtractor._paragraphs(body))

                if ok:
                    passed += 1
                    status = "PASS"
                else:
                    failed += 1
                    status = f"FAIL:{reason}"

                print(
                    f"ARTICLE[{index}]={status} "
                    f"title={json.dumps(title, ensure_ascii=False)} "
                    f"body_chars={len(body)} paragraphs={paragraphs} "
                    f"final_url={response.url}"
                )
            except Exception as exc:
                failed += 1
                print(f"ARTICLE[{index}]=ERROR {type(exc).__name__}: {exc}")

            time.sleep(0.5)

    print(
        f"EXTRACTION_SUMMARY passed={passed} failed={failed} "
        f"discovered={len(refs)}"
    )

    if passed == 0:
        print("RESULT=FAIL: no article passed extraction Quality Gate")
        return 1

    print("RESULT=PASS: at least one live article passed extraction Quality Gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
