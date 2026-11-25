import json

from tangthu_crawler.marker import SourceMarkerRegistry


def test_marker_is_created_per_source_url_and_applied(tmp_path):
    registry = SourceMarkerRegistry(tmp_path / "source_markers.json")
    sources = [
        {
            "id": "vn-home",
            "url": "https://vnexpress.net/",
            "site_adapter": "vnexpress",
            "discovery": ["html"],
            "html": {"strategy": "page_articles", "article_container_selectors": ["#paging"]},
            "extractor": {"engine": "vnexpress"},
        },
        {
            "id": "vn-topic",
            "url": "https://vnexpress.net/goc-nhin",
            "site_adapter": "vnexpress",
            "discovery": ["html"],
            "html": {"strategy": "page_articles", "article_container_selectors": [".list-article"]},
            "extractor": {"engine": "vnexpress"},
        },
    ]

    assert registry.ensure_sources(sources) == 2
    registry.save()

    home = registry.get("vn-home")
    topic = registry.get("vn-topic")
    assert home["domain"] == topic["domain"] == "vnexpress.net"
    assert home["profile"]["html"]["article_container_selectors"] == ["#paging"]
    assert topic["profile"]["html"]["article_container_selectors"] == [".list-article"]
    assert home["status"] == topic["status"] == "pending"

    target = {"id": "vn-home", "url": "https://vnexpress.net/"}
    registry.apply(target)
    assert target["site_adapter"] == "vnexpress"
    assert target["html"]["article_container_selectors"] == ["#paging"]


def test_ensure_is_idempotent_and_does_not_overwrite_marker(tmp_path):
    path = tmp_path / "source_markers.json"
    registry = SourceMarkerRegistry(path)
    source = {
        "id": "s1",
        "url": "https://example.com/news",
        "discovery": ["html"],
        "html": {"strategy": "generic"},
        "extractor": {"engine": "trafilatura"},
    }
    assert registry.ensure_sources([source]) == 1
    registry.save()

    data = json.loads(path.read_text(encoding="utf-8"))
    data["markers"][0]["status"] = "verified"
    data["markers"][0]["analysis"]["note"] = "Analyzer passed"
    path.write_text(json.dumps(data), encoding="utf-8")

    second = SourceMarkerRegistry(path)
    assert second.ensure_sources([source]) == 0
    second.save()
    marker = second.get("s1")
    assert marker["status"] == "verified"
    assert marker["analysis"]["note"] == "Analyzer passed"


def test_missing_marker_is_an_error_on_apply(tmp_path):
    registry = SourceMarkerRegistry(tmp_path / "source_markers.json")
    try:
        registry.apply({"id": "missing"})
    except KeyError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("Expected KeyError")


def test_marker_update_records_analyzer_decision(tmp_path):
    registry = SourceMarkerRegistry(tmp_path / "source_markers.json")
    registry.ensure_sources([{"id": "s1", "url": "https://example.com"}])
    marker = registry.update(
        "s1",
        adapter_id="generic_html",
        status="verified",
        quality={"score": 92, "sample_size": 5, "passed": True},
        analysis={"last_analyzed_at": "2026-11-25T00:00:00Z", "note": "passed"},
    )
    assert marker["status"] == "verified"
    assert marker["quality"]["score"] == 92
    assert marker["analysis"]["note"] == "passed"


def test_fixed_marker_requires_explicit_override(tmp_path):
    registry = SourceMarkerRegistry(tmp_path / "source_markers.json")
    registry.ensure_sources([{"id": "s1", "url": "https://example.com"}])
    registry.update("s1", status="fixed", analysis={"note": "Manually pinned"})

    try:
        registry.update("s1", status="verified")
    except ValueError as exc:
        assert "force=True" in str(exc)
    else:
        raise AssertionError("Expected fixed marker to reject implicit update")

    marker = registry.update("s1", status="verified", force=True)
    assert marker["status"] == "verified"
