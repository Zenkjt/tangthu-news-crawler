from tangthu_crawler.crawler import ArticleSpider


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


def test_filename_is_stable():
    url = "https://example.com/article/123"
    assert ArticleSpider._filename(url) == ArticleSpider._filename(url)
    assert len(ArticleSpider._filename(url)) == 32
