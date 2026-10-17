# Tàng Thư News Crawler — Phase 3 Checkpoint

Date: 17 October 2026

## Completed

Integrated Scrapy as the generic crawl engine after Discovery.

Pipeline:

```text
Source Registry
      ↓
SourceDiscovery
      ↓
ArticleRef URL pool
      ↓
Scrapy ArticleSpider
      ↓
raw HTML
      ↓
data/article_pool/<source_id>/<sha256(url)[:32]>.html
```

## Decisions

- Scrapy is the crawl engine, not the article extractor.
- The spider is generic; it is not hard-coded for VnExpress.
- Discovery remains responsible for finding and canonicalizing article URLs.
- Scrapy receives `ArticleRef` objects from Discovery.
- Concurrency, timeout and retry values come from `config/settings.yaml`.
- `ROBOTSTXT_OBEY` is enabled.
- Only the configured source domain and its subdomains are accepted.
- Raw HTML is stored in the Article Pool for the next extraction phase.
- The filename is a stable SHA-256 prefix derived from the canonical URL.
- No newspaper4k, EPUB generation, Drive upload or OPDS logic is added in this phase.

## Next phase

Phase 4: newspaper4k article extraction from the raw HTML/article pool.
