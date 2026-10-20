
from pathlib import Path

from tangthu_crawler.article_cache import ArticleCache
from tangthu_crawler.crawl_planner import CrawlPlanner


def sub(branch, source, count=5, mode="text"):
    return {
        "id": f"{branch}-{source}",
        "branch_id": branch,
        "source_id": source,
        "article_count": count,
        "edition_mode": mode,
        "enabled": True,
    }


def article(source, url, fetched="2026-10-20T00:00:00Z", images=None):
    return {
        "source_id": source,
        "canonical_url": url,
        "title": "Article",
        "content": "Body",
        "excerpt": "Excerpt",
        "fetched_at": fetched,
        "images": images or [],
    }


def test_existing_cache_means_no_crawl(tmp_path: Path):
    cache = ArticleCache(tmp_path / "cache")
    for i in range(5):
        cache.upsert(article("s1", f"https://example.com/{i}"))

    plan = CrawlPlanner().plan_on_demand(
        "b1",
        [sub("b1", "s1", 5)],
        cache,
        now="2026-10-20T12:00:00Z",
    )

    assert plan.sources_to_crawl == []
    assert plan.cache_only_sources == ["s1"]


def test_new_source_crawls_only_that_source(tmp_path: Path):
    cache = ArticleCache(tmp_path / "cache")
    for i in range(5):
        cache.upsert(article("s1", f"https://example.com/{i}"))

    plan = CrawlPlanner().plan_on_demand(
        "b1",
        [sub("b1", "s1", 5), sub("b1", "s2", 5)],
        cache,
        now="2026-10-20T12:00:00Z",
    )

    assert plan.sources_to_crawl == ["s2"]
    assert plan.cache_only_sources == ["s1"]


def test_daily_crawls_each_source_once_across_branches(tmp_path: Path):
    cache = ArticleCache(tmp_path / "cache")
    subscriptions = [
        sub("b1", "s1", 5),
        sub("b2", "s1", 10),
        sub("b1", "s2", 5),
    ]

    plan = CrawlPlanner().plan_daily(
        subscriptions,
        cache,
        now="2026-10-20T12:00:00Z",
    )

    assert plan.sources_to_crawl == ["s1", "s2"]
    assert [d.target_count for d in plan.decisions] == [10, 5]


def test_expired_cache_is_not_usable(tmp_path: Path):
    cache = ArticleCache(tmp_path / "cache")
    for i in range(5):
        cache.upsert(
            article(
                "s1",
                f"https://example.com/{i}",
                fetched="2026-10-14T00:00:00Z",
            )
        )

    plan = CrawlPlanner().plan_on_demand(
        "b1",
        [sub("b1", "s1", 5)],
        cache,
        now="2026-10-20T00:00:00Z",
    )

    assert plan.sources_to_crawl == ["s1"]
    assert plan.decisions[0].valid_cached_count == 0


def test_images_mode_requires_images(tmp_path: Path):
    cache = ArticleCache(tmp_path / "cache")
    cache.upsert(article("s1", "https://example.com/text"))
    cache.upsert(
        article(
            "s1",
            "https://example.com/image",
            images=["https://example.com/a.jpg"],
        )
    )

    plan = CrawlPlanner().plan_on_demand(
        "b1",
        [sub("b1", "s1", 1, "images")],
        cache,
        now="2026-10-20T12:00:00Z",
    )

    assert plan.sources_to_crawl == []
    assert plan.decisions[0].valid_cached_count == 1


def test_cancelled_branch_does_nothing(tmp_path: Path):
    cache = ArticleCache(tmp_path / "cache")

    plan = CrawlPlanner().plan_on_demand(
        "b1",
        [],
        cache,
        now="2026-10-20T12:00:00Z",
    )

    assert plan.cancelled is True
    assert plan.decisions == []
    assert plan.sources_to_crawl == []
