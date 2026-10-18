from tangthu_crawler.discovery import SourceDiscovery


def test_page_articles_does_not_fallback_to_generic_links(monkeypatch):
    html = """
    <article><h3 class="title-news"><a href="/tin-hop-le-123456.html">Bài 1</a></h3></article>
    <a href="/tac-gia/vo-ta-han-50.html">Tác giả</a>
    """
    source = {
        "id": "vnexpress",
        "url": "https://vnexpress.net",
        "discovery": ["html"],
        "html": {
            "strategy": "page_articles",
            "max_articles": 20,
            "article_link_selectors": [".title-news a"],
        },
    }
    discovery = SourceDiscovery(source, {"crawler": {"request_timeout": 5, "user_agent": "test"}})
    monkeypatch.setattr(discovery, "_get", lambda url: html)

    assert [ref.url for ref in discovery.discover()] == [
        "https://vnexpress.net/tin-hop-le-123456.html"
    ]
