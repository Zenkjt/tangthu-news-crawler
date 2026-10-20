from pathlib import Path
from tangthu_crawler.article_cache import ArticleCache


def article(source_id, url, fetched_at="2026-10-20T00:00:00Z", images=None):
    return {
        "source_id": source_id, "canonical_url": url, "title": "Test article",
        "content": "Article body", "excerpt": "Article excerpt",
        "published_at": "2026-10-20T00:00:00Z",
        "discovered_at": "2026-10-20T00:00:00Z", "fetched_at": fetched_at,
        "images": images or [], "content_mode": "full_article",
    }


def test_upsert_and_get(tmp_path: Path):
    cache = ArticleCache(tmp_path / "article_cache")
    cache.upsert(article("s1", "https://example.com/a"))
    got = cache.get("s1", "https://example.com/a", now="2026-10-20T12:00:00Z")
    assert got is not None
    assert got["expires_at"] == "2026-10-25T00:00:00Z"


def test_same_source_and_url_updates_existing_record(tmp_path: Path):
    cache = ArticleCache(tmp_path / "article_cache")
    cache.upsert(article("s1", "https://example.com/a"))
    updated = article("s1", "https://example.com/a")
    updated["title"] = "Updated"
    cache.upsert(updated)
    records = cache.all_records("s1")
    assert len(records) == 1 and records[0]["title"] == "Updated"


def test_same_url_different_sources_are_separate(tmp_path: Path):
    cache = ArticleCache(tmp_path / "article_cache")
    cache.upsert(article("s1", "https://example.com/a"))
    cache.upsert(article("s2", "https://example.com/a"))
    assert len(cache.all_records("s1")) == 1
    assert len(cache.all_records("s2")) == 1


def test_exact_five_day_lifetime(tmp_path: Path):
    cache = ArticleCache(tmp_path / "article_cache")
    cache.upsert(article("s1", "https://example.com/a"))
    assert cache.get("s1", "https://example.com/a", now="2026-10-24T23:59:59Z")
    assert cache.get("s1", "https://example.com/a", now="2026-10-25T00:00:00Z") is None


def test_refresh_resets_five_day_clock(tmp_path: Path):
    cache = ArticleCache(tmp_path / "article_cache")
    cache.upsert(article("s1", "https://example.com/a"))
    cache.upsert(article("s1", "https://example.com/a", fetched_at="2026-10-22T06:00:00Z"))
    got = cache.get("s1", "https://example.com/a", now="2026-10-26T05:59:59Z")
    assert got is not None
    assert got["expires_at"] == "2026-10-27T06:00:00Z"


def test_images_mode_requires_cached_images(tmp_path: Path):
    cache = ArticleCache(tmp_path / "article_cache")
    cache.upsert(article("s1", "https://example.com/text"))
    cache.upsert(article("s1", "https://example.com/image", images=["https://example.com/image.jpg"]))
    assert cache.valid_count("s1", now="2026-10-20T12:00:00Z", edition_mode="text") == 2
    assert cache.valid_count("s1", now="2026-10-20T12:00:00Z", edition_mode="images") == 1


def test_cleanup_removes_only_expired_records(tmp_path: Path):
    cache = ArticleCache(tmp_path / "article_cache")
    cache.upsert(article("s1", "https://example.com/old", fetched_at="2026-10-14T00:00:00Z"))
    cache.upsert(article("s1", "https://example.com/new", fetched_at="2026-10-20T00:00:00Z"))
    assert cache.cleanup_expired(now="2026-10-20T12:00:00Z") == 1
    assert cache.get("s1", "https://example.com/old", include_expired=True) is None
    assert cache.get("s1", "https://example.com/new", now="2026-10-20T12:00:00Z") is not None
