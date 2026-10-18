from tangthu_crawler.discovery import SourceDiscovery


def test_configurable_article_href_regex_for_cnn():
    source = {
        "id": "cnn",
        "url": "https://www.cnn.com/",
        "html": {
            "article_href_regex": r"^/\d{4}/\d{2}/\d{2}/[^?#]+(?:/index\.html)?$",
            "excluded_path_prefixes": [],
        },
    }
    discovery = SourceDiscovery(source, {"crawler": {}})
    assert discovery._is_article_url("https://www.cnn.com/2026/10/17/world/example/index.html")
    assert not discovery._is_article_url("https://www.cnn.com/world")
    assert not discovery._is_article_url("https://www.cnn.com/videos/example/index.html")
