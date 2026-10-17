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


def test_vnexpress_falls_back_to_content_detail(tmp_path):
    html = """
    <html><body>
      <h1 class="title-detail">Bài đặc biệt</h1>
      <article class="content_detail">
        <div id="article_content">
          <p>Đoạn nội dung một.</p>
          <p>Đoạn nội dung hai.</p>
        </div>
      </article>
    </body></html>
    """
    path = tmp_path / "article.html"
    path.write_text(html, encoding="utf-8")
    article = ArticleExtractor().extract(
        path,
        "https://vnexpress.net/test-special-456.html",
        {"extractor": {"engine": "vnexpress"}},
    )
    assert "Đoạn nội dung một." in article["body"]
    assert "Đoạn nội dung hai." in article["body"]


def test_vnexpress_generic_container_fallback(tmp_path):
    html = """
    <html><body>
      <h1 class="title-detail">Bài dùng template khác</h1>
      <main class="article-shell">
        <p>Đoạn nội dung thứ nhất của bài báo.</p>
        <p>Đoạn nội dung thứ hai của bài báo.</p>
        <p>Đoạn nội dung thứ ba của bài báo.</p>
      </main>
    </body></html>
    """
    path = tmp_path / "article.html"
    path.write_text(html, encoding="utf-8")

    article = ArticleExtractor().extract(
        path,
        "https://vnexpress.net/test-789.html",
        {"extractor": {"engine": "vnexpress"}},
    )

    assert "Đoạn nội dung thứ nhất" in article["body"]
    assert "Đoạn nội dung thứ ba" in article["body"]


def test_vnexpress_decodes_double_encoded_html_entities(tmp_path):
    html = """
    <html><body>
      <h1 class="title-detail">Nga ca ngợi &amp;#x27;khoảnh khắc lịch sử&amp;#x27;</h1>
      <article class="fck_detail">
        <p>Ông nói &amp;quot;đây là một bước ngoặt&amp;quot;.</p>
        <p>Đây là đoạn thứ hai của bài báo.</p>
      </article>
    </body></html>
    """
    path = tmp_path / "article.html"
    path.write_text(html, encoding="utf-8")

    article = ArticleExtractor().extract(
        path,
        "https://vnexpress.net/test-entities-123.html",
        {"extractor": {"engine": "vnexpress"}},
    )

    assert "'khoảnh khắc lịch sử'" in article["title"]
    assert '"đây là một bước ngoặt".' in article["body"]
    assert "&amp;quot;" not in article["body"]
    assert "&#x27;" not in article["body"]
