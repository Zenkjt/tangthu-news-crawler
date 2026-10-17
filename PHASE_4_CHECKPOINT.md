# Tàng Thư News Crawler — Phase 4 Checkpoint

Date: 17 October 2026

## Fix 2

The previous implementation passed `input_html` to `Article(...)`, but newspaper4k's current API expects cached HTML in:

```python
article.download(input_html=html)
article.parse()
```

The `download(input_html=...)` path sets `download_state=SUCCESS` and stores the supplied HTML without performing an HTTP request. The subsequent `parse()` then works normally.

`canonical_url` now uses `article.canonical_link` when available.

## Decision

Scrapy remains the only network crawler. newspaper4k receives the already-downloaded HTML and never performs a second article request.

Reference: newspaper4k `Article.download()` documents `input_html` as cached article HTML and its source sets the successful download state before `parse()`.
