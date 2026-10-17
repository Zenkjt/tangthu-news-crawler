from tangthu_crawler.extractor import ArticleExtractor


def test_vnexpress_extracts_full_fck_detail(tmp_path):
    html = """
    <html><head><link rel="canonical" href="https://vnexpress.net/test-123.html"></head>
    <body>
      <h1 class="title-detail">Tiêu đề bài viết</h1>
      <span class="date">17/10/2026, 10:30 (GMT+7)</span>
      <p class="description">Đây là sapo.</p>
      <article class="fck_detail">
        <p class="Normal">Đoạn thứ nhất.</p>
        <p class="Normal">Đoạn thứ hai.</p>
        <p class="Normal">Đoạn thứ ba.</p>
        <figure><figcaption>Chú thích ảnh.</figcaption></figure>
      </article>
    </body></html>
    """
    path = tmp_path / "article.html"
    path.write_text(html, encoding="utf-8")
    article = ArticleExtractor().extract(
        path,
        "https://vnexpress.net/test-123.html",
        {"extractor": {"engine": "vnexpress"}},
    )
    assert article["title"] == "Tiêu đề bài viết"
    assert "Đoạn thứ nhất." in article["body"]
    assert "Đoạn thứ ba." in article["body"]
    assert "Chú thích ảnh." in article["body"]
    assert "Đây là sapo." in article["body"]
    assert article["published_at"].startswith("2026-10-17T10:30:00+07:00")
