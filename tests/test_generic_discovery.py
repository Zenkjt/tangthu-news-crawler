from tangthu_crawler.discovery import SourceDiscovery


def test_generic_discovery_scores_date_article_and_rejects_topic_video():
    source = {
        "id": "bbc-vietnamese",
        "url": "https://www.bbc.com/vietnamese/topics/cnlv9j1ekq0t",
        "html": {"min_link_score": 4, "excluded_path_prefixes": []},
    }
    d = SourceDiscovery(source, {"crawler": {}})
    assert d._score_link(_anchor("https://www.bbc.com/vietnamese/articles/c12345678"), "/vietnamese/articles/c12345678", ()) >= 4
    assert d._score_link(_anchor("https://www.cnn.com/2026/10/18/world/example/index.html"), "/2026/10/18/world/example/index.html", ()) >= 4
    assert d._score_link(_anchor("https://www.bbc.com/vietnamese/topics/cnlv9j1ekq0t"), "/vietnamese/topics/cnlv9j1ekq0t", d.EXCLUDED_PREFIXES) < 4
    assert d._score_link(_anchor("https://www.bbc.com/vietnamese/videos/c123"), "/vietnamese/videos/c123", d.EXCLUDED_PREFIXES) < 0


def _anchor(href):
    from bs4 import BeautifulSoup
    return BeautifulSoup(f'<a href="{href}">Một tiêu đề bài viết quốc tế rất dài để chấm điểm</a>', "html.parser").a
