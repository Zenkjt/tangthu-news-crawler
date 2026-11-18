from tangthu_crawler.pipeline import _resolve_sources


def test_registry_mapping_matches_www_hostname_alias():
    local = [{
        "id": "vnexpress",
        "name": "VnExpress",
        "url": "https://vnexpress.net",
        "status": "active",
        "discovery": ["html"],
        "html": {"strategy": "page_articles", "max_articles": 20},
        "extractor": {"engine": "vnexpress"},
        "policy": {"mode": "full_article"},
    }]
    resolved, mapping = _resolve_sources(
        [{
            "id": "s-www",
            "url": "https://www.vnexpress.net/thoi-su/ha-noi-today",
            "name": "VnExpress Hà Nội",
            "enabled": True,
            "order": 1,
        }],
        local,
    )
    assert len(resolved) == 1
    assert mapping["s-www"]["extractor"]["engine"] == "vnexpress"
    assert mapping["s-www"]["policy"]["mode"] == "full_article"
    assert mapping["s-www"]["url"] == "https://www.vnexpress.net/thoi-su/ha-noi-today"
