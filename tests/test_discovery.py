from datetime import datetime,timezone
from tangthu_crawler.discovery import SourceDiscovery
from tangthu_crawler.pipeline import _is_today_or_undated

def test_page_articles_limits_to_20_and_does_not_paginate(monkeypatch):
    html="".join(f'<article><h2 class="title-news"><a href="/tin-{i}-{1000+i}.html">Tin</a></h2></article>' for i in range(25))
    source={"id":"vnexpress","url":"https://vnexpress.net/chu-de/thanh-pho-ha-noi-2056","discovery":["html"],"html":{"strategy":"page_articles","max_articles":20,"article_link_selectors":[".title-news a"]}}
    d=SourceDiscovery(source,{"crawler":{"request_timeout":5,"user_agent":"test"}}); calls=[]
    monkeypatch.setattr(d,"_get",lambda url:calls.append(url) or html)
    refs=d.discover()
    assert len(refs)==20
    assert calls==["https://vnexpress.net/chu-de/thanh-pho-ha-noi-2056"]

def test_regex_fallback(monkeypatch):
    source={"id":"vnexpress","url":"https://vnexpress.net","discovery":["html"],"html":{"strategy":"page_articles","max_articles":20,"article_link_selectors":[]}}
    d=SourceDiscovery(source,{"crawler":{"request_timeout":5,"user_agent":"test"}})
    monkeypatch.setattr(d,"_get",lambda url='<a href="/tin-hop-le-123456.html">Tin</a><a href="/video-abc">Video</a>')
    assert [r.url for r in d.discover()]==["https://vnexpress.net/tin-hop-le-123456.html"]

def test_today_and_undated_are_kept():
    assert _is_today_or_undated(datetime.now(timezone.utc).isoformat(),"Asia/Ho_Chi_Minh")
    assert _is_today_or_undated(None,"Asia/Ho_Chi_Minh")

def test_old_is_dropped():
    assert not _is_today_or_undated("2020-01-01T10:00:00+07:00","Asia/Ho_Chi_Minh")
