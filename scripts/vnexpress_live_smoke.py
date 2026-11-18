from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

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
        "max_pages": 1,
        "article_container_selectors": ["#paging, #list-news"],
        "article_link_selectors": [
            "article.item-news h3.title-news a",
            "article.item-news h2.title-news a",
        ],
        "next_page_selectors": [],
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


def _print_page_diagnostics(response: requests.Response) -> None:
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else "(no title)"
    content_type = response.headers.get("Content-Type", "(unknown)")
    print(f"DIAG_HTTP_STATUS={response.status_code}")
    print(f"DIAG_FINAL_URL={response.url}")
    print(f"DIAG_CONTENT_TYPE={content_type}")
    print(f"DIAG_HTML_BYTES={len(response.content)}")
    print(f"DIAG_TITLE={json.dumps(title, ensure_ascii=False)}")

    found = []
    for selector in ("#paging", "#list-news"):
        node = soup.select_one(selector)
        if node:
            count = len(node.select("article.item-news"))
            found.append(selector)
            print(
                f"DIAG_CONTAINER selector={selector} tag={node.name} "
                f"class={node.get('class', [])} article_cards={count}"
            )
        else:
            print(f"DIAG_CONTAINER selector={selector} NOT_FOUND")

    if found:
        return

    print("DIAG_CONTAINER_CANDIDATES_BEGIN")
    candidates = soup.find_all(
        lambda tag: tag.name in {"div", "section", "main"}
        and (
            any(word in str(tag.get("id", "")).lower()
                for word in ("list", "news", "paging", "stream", "article"))
            or any(word in " ".join(tag.get("class", [])).lower()
                   for word in ("list-news", "stream", "article", "news-list"))
        ),
        limit=20,
    )
    for index, node in enumerate(candidates, start=1):
        text_excerpt = node.get_text(" ", strip=True)[:220]
        print(
            f"DIAG_CANDIDATE[{index}] tag={node.name} id={node.get('id', '')!r} "
            f"class={node.get('class', [])!r} "
            f"articles={len(node.select('article'))} "
            f"text={json.dumps(text_excerpt, ensure_ascii=False)}"
        )
    print("DIAG_CONTAINER_CANDIDATES_END")

    body_text = soup.get_text(" ", strip=True).lower()
    markers = (
        "cloudflare", "access denied", "captcha", "robot",
        "verify you are human", "temporarily unavailable",
        "dịch vụ không khả dụng", "truy cập bị từ chối",
    )
    matched = [marker for marker in markers if marker in body_text]
    print(f"DIAG_BLOCK_MARKERS={matched}")
    snippet = response.text[:1800].replace("\r", " ").replace("\n", " ")
    print(f"DIAG_HTML_HEAD={json.dumps(snippet, ensure_ascii=False)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--max-articles", type=int, default=5)
    parser.add_argument("--max-pages", type=int, default=1)
    args = parser.parse_args()

    if not valid_topic_url(args.url):
        print("ERROR: URL must use vnexpress.net or www.vnexpress.net")
        return 2

    source = dict(SOURCE_BASE)
    source["url"] = args.url
    source["html"] = dict(SOURCE_BASE["html"])
    source["html"]["max_articles"] = max(1, min(args.max_articles, 100))
    # This diagnostic run deliberately tests one page only; pagination is
    # disabled so the result isolates the topic-page DOM.
    source["html"]["max_pages"] = 1

    settings = {"crawler": {"request_timeout": 25}}
    print(f"SMOKE_SOURCE={args.url}")
    print(
        "LIMITS="
        f"max_articles:{source['html']['max_articles']},"
        f"max_pages:1"
    )

    discovery = SourceDiscovery(source, settings)
    discovery.session.headers.update(DEFAULT_HEADERS)

    # Fetch once for diagnostics, then replay that exact response to the
    # adapter. This guarantees the diagnostic describes the HTML discovery
    # actually sees, without introducing a second independent page response.
    session = discovery.session
    original_get = session.get
    try:
        first_response = original_get(
            args.url, timeout=25, allow_redirects=True
        )
        _print_page_diagnostics(first_response)
    except requests.RequestException as exc:
        print(f"DIAG_REQUEST_ERROR={type(exc).__name__}: {exc}")
        first_response = None

    first_call = True

    def get_with_cached_first_response(url, **kwargs):
        nonlocal first_call
        if first_call and first_response is not None:
            first_call = False
            return first_response
        first_call = False
        return original_get(url, **kwargs)

    session.get = get_with_cached_first_response
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
    article_session = requests.Session()
    article_session.headers.update(DEFAULT_HEADERS)

    with tempfile.TemporaryDirectory(prefix="vnexpress-smoke-") as temp_dir:
        temp_path = Path(temp_dir)

        for index, ref in enumerate(refs, start=1):
            try:
                response = article_session.get(
                    ref.url, timeout=25, allow_redirects=True
                )
                response.raise_for_status()

                final_host = (urlparse(response.url).hostname or "").lower()
                if final_host not in {"vnexpress.net", "www.vnexpress.net"}:
                    raise ValueError(
                        f"article redirected outside VnExpress: {response.url}"
                    )

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
                print(
                    f"ARTICLE[{index}]=ERROR "
                    f"{type(exc).__name__}: {exc}"
                )

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
