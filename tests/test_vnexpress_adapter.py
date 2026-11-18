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
            "article_link_selectors": [".title-news a", "article h3 a"],
        },
    }


def test_topic_adapter_collects_article_links_and_rejects_non_articles(monkeypatch):
    start = "https://vnexpress.net/goc-nhin"
    html = """
    <html><body>
      <article><h3 class="title-news"><a href="/bai-viet-thu-nhat-5133001.html">Bài 1</a></h3></article>
      <article><h3 class="title-news"><a href="/bai-viet-thu-hai-5133002.html">Bài 2</a></h3></article>
      <a href="/tac-gia/vo-ta-han-50.html">Tác giả</a>
      <a href="/tag/goc-nhin-123">Tag</a>
      <a href="https://example.com/bai-viet-123.html">External</a>
    </body></html>
    """
    source = make_source(start)
    discovery = SourceDiscovery(source, {"crawler": {"request_timeout": 5}})
    fake = FakeSession({start: html})
    discovery.session = fake

    refs = discovery.discover()

    assert [ref.url for ref in refs] == [
        "https://vnexpress.net/bai-viet-thu-nhat-5133001.html",
        "https://vnexpress.net/bai-viet-thu-hai-5133002.html",
    ]
    assert fake.calls == [start]


def test_topic_adapter_follows_only_same_topic_pagination_and_deduplicates(monkeypatch):
    start = "https://vnexpress.net/goc-nhin/kinh-doanh-quan-tri-p1"
    page2 = "https://vnexpress.net/goc-nhin/kinh-doanh-quan-tri-p2"
    html1 = """
    <article><h3 class="title-news"><a href="/bai-a-5133001.html">Bài A</a></h3></article>
    <article><h3 class="title-news"><a href="/bai-b-5133002.html">Bài B</a></h3></article>
    <nav class="pagination"><a href="/goc-nhin/kinh-doanh-quan-tri-p2" rel="next">Tiếp</a></nav>
    <a href="/goc-nhin/chinh-tri-chinh-sach-p2">Nhánh khác</a>
    """
    html2 = """
    <article><h3 class="title-news"><a href="/bai-b-5133002.html">Bài B lặp</a></h3></article>
    <article><h3 class="title-news"><a href="/bai-c-5133003.html">Bài C</a></h3></article>
    """
    source = make_source(start)
    discovery = SourceDiscovery(source, {"crawler": {"request_timeout": 5}})
    fake = FakeSession({start: html1, page2: html2})
    discovery.session = fake

    refs = discovery.discover()

    assert [ref.url for ref in refs] == [
        "https://vnexpress.net/bai-a-5133001.html",
        "https://vnexpress.net/bai-b-5133002.html",
        "https://vnexpress.net/bai-c-5133003.html",
    ]
    assert fake.calls == [start, page2]


def test_topic_adapter_obeys_article_and_page_limits():
    start = "https://vnexpress.net/goc-nhin"
    page2 = "https://vnexpress.net/goc-nhin-p2"
    html1 = """
    <article><h3 class="title-news"><a href="/bai-a-5133001.html">Bài A</a></h3></article>
    <nav class="pagination"><a href="/goc-nhin-p2">2</a></nav>
    """
    html2 = """
    <article><h3 class="title-news"><a href="/bai-b-5133002.html">Bài B</a></h3></article>
    <nav class="pagination"><a href="/goc-nhin-p3">3</a></nav>
    """
    source = make_source(start, max_articles=1, max_pages=3)
    discovery = SourceDiscovery(source, {"crawler": {"request_timeout": 5}})
    fake = FakeSession({start: html1, page2: html2})
    discovery.session = fake

    refs = discovery.discover()

    assert len(refs) == 1
    assert refs[0].url.endswith("bai-a-5133001.html")
    assert fake.calls == [start]


def test_topic_profile_keeps_its_own_start_url():
    topic_url = "https://vnexpress.net/goc-nhin/van-hoa-loi-song"
    html = '<article><h3 class="title-news"><a href="/bai-van-hoa-5133004.html">Bài</a></h3></article>'
    source = make_source(topic_url)
    discovery = SourceDiscovery(source, {"crawler": {"request_timeout": 5}})
    fake = FakeSession({topic_url: html})
    discovery.session = fake

    refs = discovery.discover()

    assert fake.calls == [topic_url]
    assert refs[0].url.endswith("bai-van-hoa-5133004.html")
