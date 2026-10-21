from pathlib import Path

from tangthu_crawler.crawler import ArticleSpider
from tangthu_crawler.extractor import ArticleExtractor


def test_pagination_identity_for_vhnt_style_urls():
    root = "https://vanhoanghethuat.vn/nhung-net-77763236.html"
    page2 = "https://vanhoanghethuat.vn/nhung-net-77763236-page2.html"

    assert ArticleSpider._same_article(page2, root)
    assert ArticleSpider._page_number(page2, root) == 2


def test_pagination_identity_for_query_and_numeric_urls():
    root = "https://example.com/story-123.html"

    assert ArticleSpider._same_article(
        "https://example.com/story-123.html?page=2",
        root,
    )
    assert ArticleSpider._page_number(
        "https://example.com/story-123.html?page=2",
        root,
    ) == 2

    assert ArticleSpider._same_article(
        "https://example.com/story-123/2",
        root,
    )
    assert ArticleSpider._page_number(
        "https://example.com/story-123/2",
        root,
    ) == 2


def test_page_paths_and_merge(tmp_path: Path):
    root = tmp_path / "abc.html"
    page2 = tmp_path / "abc.page2.html"

    root.write_text(
        "<html><head><meta property='og:title' content='Bài test'></head>"
        "<body><p>Đoạn một.</p><p>Đoạn hai.</p></body></html>",
        encoding="utf-8",
    )
    page2.write_text(
        "<html><body><p>Đoạn hai.</p><p>Đoạn ba.</p></body></html>",
        encoding="utf-8",
    )

    paths = ArticleExtractor._page_paths(root)
    assert paths == [root, page2]

    merged = ArticleExtractor._merge_page_bodies(
        ["Đoạn một.\n\nĐoạn hai.", "Đoạn hai.\n\nĐoạn ba."]
    )
    assert merged == "Đoạn một.\n\nĐoạn hai.\n\nĐoạn ba."
