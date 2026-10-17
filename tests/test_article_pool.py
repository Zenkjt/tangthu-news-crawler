import json

from tangthu_crawler.article_pool import ArticlePool


def test_article_pool_paths_are_stable(tmp_path):
    pool = ArticlePool(tmp_path)

    assert pool.html_path("vnexpress", "abc").name == "abc.html"
    assert pool.metadata_path("vnexpress", "abc").name == "abc.meta.json"
    assert pool.article_path("vnexpress", "abc").name == "abc.json"


def test_write_and_read_metadata(tmp_path):
    pool = ArticlePool(tmp_path)
    path = pool.metadata_path("vnexpress", "abc")
    path.parent.mkdir(parents=True)

    path.write_text(
        json.dumps({"id": "abc", "url": "https://example.com/a"}),
        encoding="utf-8",
    )

    metadata = pool.read_metadata("vnexpress", "abc")
    assert metadata["url"] == "https://example.com/a"
