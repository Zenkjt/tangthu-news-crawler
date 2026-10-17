from pathlib import Path

from tangthu_crawler.extractor import ArticleExtractor


FIXTURE = Path(__file__).parent / "fixtures" / "article.html"


def test_extracts_core_article_fields():
    result = ArticleExtractor().extract(
        FIXTURE,
        "https://example.com/test-article",
    )

    assert result["title"] == "Test Article Title"
    assert "first paragraph" in result["body"]
    assert result["author"] == "Jane Doe"
    assert result["image"] == "https://example.com/image.jpg"
    assert result["published_at"] is not None


def test_missing_date_is_allowed():
    html = FIXTURE.read_text(encoding="utf-8").replace(
        '<meta property="article:published_time" '
        'content="2026-10-17T07:00:00+07:00">',
        "",
    )
    missing_date = FIXTURE.parent / "article-no-date.html"
    missing_date.write_text(html, encoding="utf-8")

    try:
        result = ArticleExtractor().extract(
            missing_date,
            "https://example.com/test-article",
        )
        assert result["published_at"] is None
    finally:
        missing_date.unlink(missing_ok=True)
