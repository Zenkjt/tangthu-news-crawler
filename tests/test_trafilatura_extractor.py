from types import SimpleNamespace

from tangthu_crawler.extractor import ArticleExtractor


def test_generic_uses_trafilatura(monkeypatch, tmp_path):
    html = """
    <html><head>
      <link rel="canonical" href="https://example.com/article-1">
      <meta property="og:image" content="/cover.jpg">
    </head><body><h1>Fallback title</h1></body></html>
    """
    path = tmp_path / "article.html"
    path.write_text(html, encoding="utf-8")

    fake = SimpleNamespace(
        title="Trafilatura title",
        author="Nguyen Van A",
        date="2026-10-21T08:30:00+07:00",
        url="https://example.com/article-1",
        text="\n\n".join([
            "Đoạn nội dung thứ nhất đủ dài để kiểm tra bộ máy trích xuất.",
            "Đoạn nội dung thứ hai tiếp tục phần thân bài và không phải nội dung điều hướng.",
            "Đoạn nội dung thứ ba giúp kiểm tra rằng toàn bộ phần thân được giữ lại.",
        ]),
    )
    calls = []

    def fake_bare_extraction(*args, **kwargs):
        calls.append(kwargs)
        return fake

    monkeypatch.setattr("tangthu_crawler.extractor.bare_extraction", fake_bare_extraction)

    article = ArticleExtractor().extract(path, "https://example.com/article-1")

    assert calls
    assert calls[0]["favor_recall"] is True
    assert calls[0]["include_comments"] is False
    assert article["title"] == "Trafilatura title"
    assert article["author"] == "Nguyen Van A"
    assert "Đoạn nội dung thứ ba" in article["body"]
    assert article["canonical_url"] == "https://example.com/article-1"
    assert article["image"] == "https://example.com/cover.jpg"


def test_generic_uses_newspaper4k_only_as_rescue(monkeypatch, tmp_path):
    path = tmp_path / "article.html"
    path.write_text("<html><body><h1>Test</h1></body></html>", encoding="utf-8")

    short = SimpleNamespace(
        title="Short",
        author=None,
        date=None,
        url="https://example.com/1",
        text="quá ngắn",
    )
    monkeypatch.setattr("tangthu_crawler.extractor.bare_extraction", lambda *a, **k: short)

    rescue = {
        "url": "https://example.com/1",
        "canonical_url": "https://example.com/1",
        "title": "Rescued",
        "author": None,
        "published_at": None,
        "body": "\n\n".join(["Đoạn một đủ dài.", "Đoạn hai đủ dài.", "Đoạn ba đủ dài."]) * 30,
        "image": None,
    }
    calls = []

    def fake_rescue(*args, **kwargs):
        calls.append(True)
        return rescue

    monkeypatch.setattr(ArticleExtractor, "_extract_newspaper4k", fake_rescue)

    article = ArticleExtractor().extract(path, "https://example.com/1")
    assert calls == [True]
    assert article["title"] == "Rescued"


def test_quality_gate_keeps_existing_contract():
    ok, reason = ArticleExtractor.quality_check(
        {
            "title": "Bài viết",
            "body": "Đoạn một\n\nĐoạn hai đủ dài",
        },
        {
            "quality_gate": {
                "enabled": True,
                "require_title": True,
                "min_body_chars": 10,
                "min_paragraphs": 2,
            }
        },
    )
    assert ok is True
    assert reason == ""
