from datetime import datetime, timezone

from tangthu_crawler.discovery import SourceDiscovery


def test_canonicalize_removes_tracking_and_trailing_slash():
    result = SourceDiscovery._canonicalize(
        "https://vnexpress.net/example/?utm_source=test"
    )
    assert result == "https://vnexpress.net/example"


def test_canonicalize_rejects_invalid_url():
    assert SourceDiscovery._canonicalize("not-a-url") is None


def test_category_pagination_discovers_vietnamese_article_links(monkeypatch):
    pages = {
        "https://vnexpress.net/kinh-doanh-p1": """
            <article><h2 class="title-news">
              <a href="/bai-mot-123.html">Bài một</a>
            </h2></article>
            <article><h2 class="title-news">
              <a href="/bai-hai-456.html?utm_source=x">Bài hai</a>
            </h2></article>
        """,
        "https://vnexpress.net/kinh-doanh-p2": "",
    }

    source = {
        "id": "vnexpress",
        "url": "https://vnexpress.net",
        "discovery": ["html"],
        "html": {
            "strategy": "category_pagination",
            "page_url_template": "/{category}-p{page}",
            "article_link_selector": ".title-news a",
            "categories": ["kinh-doanh"],
            "pages": 3,
        },
    }
    discovery = SourceDiscovery(
        source,
        {"crawler": {"request_timeout": 5, "user_agent": "test"}},
    )
    monkeypatch.setattr(
        discovery,
        "_get",
        lambda url: pages[url],
    )

    refs = discovery.discover()

    assert [ref.url for ref in refs] == [
        "https://vnexpress.net/bai-mot-123.html",
        "https://vnexpress.net/bai-hai-456.html",
    ]
