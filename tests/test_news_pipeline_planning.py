from __future__ import annotations

import pytest

from tangthu_crawler.pipeline import (
    _active_subscriptions,
    _canonical_url,
    _edition_limits,
    _resolve_sources,
)


def test_active_subscriptions_filter_disabled_records():
    payload = {
        "branches": [{"id": "b1", "enabled": True}, {"id": "b2", "enabled": False}],
        "sources": [{"id": "s1", "enabled": True}, {"id": "s2", "enabled": False}],
        "subscriptions": [
            {"branch_id": "b1", "source_id": "s1", "enabled": True},
            {"branch_id": "b2", "source_id": "s1", "enabled": True},
            {"branch_id": "b1", "source_id": "s2", "enabled": True},
            {"branch_id": "b1", "source_id": "s1", "enabled": False},
        ],
    }
    assert _active_subscriptions(payload) == [
        {"branch_id": "b1", "source_id": "s1", "enabled": True}
    ]
    assert _active_subscriptions(payload, "b2") == []


def test_canonical_url_normalization():
    assert _canonical_url("https://example.com/category/#top") == "https://example.com/category"


def test_registry_mapping_keeps_local_adapter_and_safe_generic_fallback():
    local = [
        {
            "id": "vnexpress",
            "name": "VnExpress",
            "url": "https://vnexpress.net",
            "status": "active",
            "discovery": ["html"],
            "html": {"strategy": "page_articles", "max_articles": 20},
            "extractor": {"engine": "vnexpress"},
            "policy": {"mode": "full_article"},
        }
    ]
    resolved, mapping = _resolve_sources(
        [
            {"id": "s1", "url": "https://vnexpress.net/", "name": "VnExpress", "enabled": True, "order": 1},
            {"id": "s2", "url": "https://example.org/news", "name": "Example", "enabled": True, "order": 2},
        ],
        local,
    )
    assert resolved[0]["id"] == "s1"
    assert resolved[0]["extractor"]["engine"] == "vnexpress"
    assert resolved[1]["id"] == "s2"
    assert resolved[1]["extractor"]["engine"] == "newspaper4k"
    assert mapping["s2"]["policy"]["mode"] == "excerpt"


def test_edition_limits():
    _edition_limits(
        [
            {"branch_id": "b1", "article_count": 100, "edition_mode": "text"},
            {"branch_id": "b1", "article_count": 100, "edition_mode": "text"},
        ]
    )
    with pytest.raises(RuntimeError):
        _edition_limits(
            [
                {"branch_id": "b1", "article_count": 100, "edition_mode": "images"},
                {"branch_id": "b1", "article_count": 1, "edition_mode": "text"},
            ]
        )


def test_active_subscription_for_one_branch_only():
    payload = {
        "branches": [{"id": "b1", "enabled": True}, {"id": "b2", "enabled": True}],
        "sources": [{"id": "s1", "enabled": True}],
        "subscriptions": [
            {"branch_id": "b1", "source_id": "s1", "enabled": True},
            {"branch_id": "b2", "source_id": "s1", "enabled": True},
        ],
    }
    assert len(_active_subscriptions(payload, "b1")) == 1
    assert _active_subscriptions(payload, "b1")[0]["branch_id"] == "b1"
