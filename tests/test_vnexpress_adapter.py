from __future__ import annotations

from tangthu_crawler.discovery import SourceDiscovery


class FakeResponse:
    def __init__(self, url: str, text: str, status_code: int = 200):
        self.url = url
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, pages: dict[str, str]):
        self.pages = pages
        self.calls: list[str] = []
        self.headers = {}

    def get(self, url, **kwargs):
        self.calls.append(url)
        if url not in self.pages:
            raise AssertionError(f"Unexpected request: {url}")
        return FakeResponse(url, self.pages[url])


def make_source(url: str, *, max_articles: int = 20, max_pages: int = 4):
    return {
        "id": "vnexpress-topic-test",
        "site_adapter": "vnexpress",
        "url": url,
        "discovery": ["html"],
        "html": {
            "max_articles": max_articles,
            "max_pages": max_pages,
            "article_container_selectors": ["#paging"],
            "article_link_selectors": [
                "article.item-news h3.title-news a, article.item-news h2.title-news a",
            ],
        },
    }


def test_topic_adapter_scopes_to_main_stream_and_preserves_dom_order():
    start = "https://vnexpress.net/goc-nhin"
    html = """
    <html><body>
      <div class="popular">
        <article class="item-news"><h3 class="title-news">
          <a href="/popular-5133009.html">Bài nổi bật</a>
        </h3></article>
      </div>
      <div id="paging" class="list-news-subfolder">
        <article class="item-news item-1"><h3 class="title-news">
          <a href="/bai-thu-nhat-5133001.html">Bài 1</a>
        </h3></article>
        <article class="item-news item-2"><h3 class="title-news">
          <a href="/bai-thu-hai-5133002.html">Bài 2</a>
        </h3></article>
        <article class="item-news close_not_qc"></article>
        <article class="item-news item-3"><h3 class="title-news">
          <a href="/bai-thu-ba-5133003.html">Bài 3</a>
        </h3></article>
        <a href="/tac-gia/vo-ta-han-50.html">Tác giả</a>
        <a href="https://example.com/bai-ngoai-5133010.html">External</a>
      </div>
    </body></html>
    """
    discovery = SourceDiscovery(make_source(start), {"crawler": {"request_timeout": 5}})
    fake = FakeSession({start: html})
    discovery.session = fake

    refs = discovery.discover()

    assert [ref.url for ref in refs] == [
        "https://vnexpress.net/bai-thu-nhat-5133001.html",
        "https://vnexpress.net/bai-thu-hai-5133002.html",
        "https://vnexpress.net/bai-thu-ba-5133003.html",
    ]
    assert fake.calls == [start]


def test_topic_adapter_follows_same_topic_pagination_and_deduplicates():
    start = "https://vnexpress.net/goc-nhin/kinh-doanh-quan-tri-p1"
    page2 = "https://vnexpress.net/goc-nhin/kinh-doanh-quan-tri-p2"
    html1 = """
    <div id="paging">
      <article><h3 class="title-news"><a href="/bai-a-5133001.html">Bài A</a></h3></article>
      <article><h3 class="title-news"><a href="/bai-b-5133002.html">Bài B</a></h3></article>
    </div>
    <nav class="pagination"><a href="/goc-nhin/kinh-doanh-quan-tri-p2" rel="next">Tiếp</a></nav>
    <a href="/goc-nhin/chinh-tri-chinh-sach-p2">Nhánh khác</a>
    """
    html2 = """
    <div id="paging">
      <article><h3 class="title-news"><a href="/bai-b-5133002.html">Bài B lặp</a></h3></article>
      <article><h3 class="title-news"><a href="/bai-c-5133003.html">Bài C</a></h3></article>
    </div>
    """
    discovery = SourceDiscovery(make_source(start), {"crawler": {"request_timeout": 5}})
    fake = FakeSession({start: html1, page2: html2})
    discovery.session = fake

    refs = discovery.discover()

    assert [ref.url for ref in refs] == [
        "https://vnexpress.net/bai-a-5133001.html",
        "https://vnexpress.net/bai-b-5133002.html",
        "https://vnexpress.net/bai-c-5133003.html",
    ]
    assert fake.calls == [start, page2]


def test_topic_profile_stops_at_article_limit():
    start = "https://vnexpress.net/goc-nhin"
    html = """
    <div id="paging">
      <article><h3 class="title-news"><a href="/bai-a-5133001.html">Bài A</a></h3></article>
      <article><h3 class="title-news"><a href="/bai-b-5133002.html">Bài B</a></h3></article>
    </div>
    """
    discovery = SourceDiscovery(
        make_source(start, max_articles=1),
        {"crawler": {"request_timeout": 5}},
    )
    fake = FakeSession({start: html})
    discovery.session = fake

    refs = discovery.discover()

    assert len(refs) == 1
    assert refs[0].url.endswith("bai-a-5133001.html")
    assert fake.calls == [start]


def test_missing_configured_container_does_not_fall_back_to_popular_links():
    start = "https://vnexpress.net/goc-nhin"
    html = """
    <div class="popular">
      <article><h3 class="title-news">
        <a href="/popular-5133009.html">Bài nổi bật</a>
      </h3></article>
    </div>
    """
    discovery = SourceDiscovery(make_source(start), {"crawler": {"request_timeout": 5}})
    fake = FakeSession({start: html})
    discovery.session = fake

    assert discovery.discover() == []


def test_topic_profile_keeps_its_own_start_url():
    topic_url = "https://vnexpress.net/goc-nhin/van-hoa-loi-song"
    html = """
    <div id="paging"><article><h3 class="title-news">
      <a href="/bai-van-hoa-5133004.html">Bài</a>
    </h3></article></div>
    """
    discovery = SourceDiscovery(make_source(topic_url), {"crawler": {"request_timeout": 5}})
    fake = FakeSession({topic_url: html})
    discovery.session = fake

    refs = discovery.discover()

    assert fake.calls == [topic_url]
    assert refs[0].url.endswith("bai-van-hoa-5133004.html")
