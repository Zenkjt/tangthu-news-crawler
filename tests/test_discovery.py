from tangthu_crawler.discovery import SourceDiscovery


def test_canonicalize_removes_tracking_and_trailing_slash():
    result = SourceDiscovery._canonicalize(
        "https://vnexpress.net/example/?utm_source=test"
    )
    assert result == "https://vnexpress.net/example"


def test_canonicalize_rejects_invalid_url():
    assert SourceDiscovery._canonicalize("not-a-url") is None
