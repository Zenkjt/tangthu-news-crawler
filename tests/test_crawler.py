from tangthu_crawler.crawler import (
    ArticleSpider,
    DEFAULT_BROWSER_USER_AGENT,
    article_id,
    build_crawler_settings,
)


def test_allowed_domain_accepts_source_and_subdomain():
    spider = ArticleSpider(
        refs=[],
        output_dir="data/article_pool",
        settings={},
        source={"url": "https://example.com"},
    )
    assert spider._allowed_domain("https://example.com/a")
    assert spider._allowed_domain("https://news.example.com/a")


def test_allowed_domain_rejects_other_domain():
    spider = ArticleSpider(
        refs=[],
        output_dir="data/article_pool",
        settings={},
        source={"url": "https://example.com"},
    )
    assert not spider._allowed_domain("https://example.org/a")


def test_article_id_is_stable():
    url = "https://example.com/article/123"
    assert article_id(url) == article_id(url)
    assert len(article_id(url)) == 32


def test_crawler_uses_browser_headers_and_single_domain_concurrency():
    cfg = build_crawler_settings({}, {"url": "https://vnexpress.net"})
    assert cfg["USER_AGENT"] == DEFAULT_BROWSER_USER_AGENT
    assert cfg["DEFAULT_REQUEST_HEADERS"]["Accept-Language"].startswith("vi")
    assert cfg["CONCURRENT_REQUESTS"] == 1
    assert cfg["CONCURRENT_REQUESTS_PER_DOMAIN"] == 1
    assert cfg["DOWNLOAD_DELAY"] == 2
    assert cfg["AUTOTHROTTLE_ENABLED"] is True
    assert cfg["AUTOTHROTTLE_TARGET_CONCURRENCY"] == 0.5
    assert 429 in cfg["RETRY_HTTP_CODES"]


def test_source_http_headers_override_defaults():
    cfg = build_crawler_settings(
        {},
        {
            "url": "https://vnexpress.net",
            "http": {"headers": {"Referer": "https://vnexpress.net/"}},
        },
    )
    assert cfg["DEFAULT_REQUEST_HEADERS"]["Referer"] == "https://vnexpress.net/"
