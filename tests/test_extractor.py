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


def test_missing_date_is_allowed():
    result = ArticleExtractor().extract(
        FIXTURE,
        "https://example.com/test-article",
    )
    assert result["published_at"] is None or isinstance(
        result["published_at"], str
    )
