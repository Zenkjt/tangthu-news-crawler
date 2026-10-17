from tangthu_crawler.discovery import SourceDiscovery
from tangthu_crawler.extractor import ArticleExtractor


def test_vnexpress_rejects_non_article_paths():
    source={"id":"vnexpress","url":"https://vnexpress.net","html":{"excluded_path_prefixes":["/tag/","/topic/"]}}
    d=SourceDiscovery(source,{})
    assert not d._is_article_url("https://vnexpress.net/tag/anti-fake-news-1596021")
    assert not d._is_article_url("https://vnexpress.net/topic/foo-22884-p3")
    assert d._is_article_url("https://vnexpress.net/mot-bai-bao-5133558.html")


def test_quality_gate_rejects_listing_like_article():
    source={"quality_gate":{"enabled":True,"require_title":True,"min_body_chars":300,"min_paragraphs":2,"reject_titles":["Untitled","Article"]}}
    ok,reason=ArticleExtractor.quality_check({"title":"Untitled","body":"x"*1000},source)
    assert not ok and reason=="generic_title"


def test_quality_gate_rejects_short_body():
    source={"quality_gate":{"enabled":True,"require_title":True,"min_body_chars":300,"min_paragraphs":2}}
    ok,reason=ArticleExtractor.quality_check({"title":"Một bài báo thật","body":"Đoạn một."},source)
    assert not ok and reason in {"body_too_short","too_few_paragraphs"}
