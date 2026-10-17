# Tàng Thư News Crawler — Phase 5 Checkpoint

Date: 17 October 2026

## Completed

Hardened the Article Pool so URL-to-file mapping is deterministic.

```text
canonical URL
    ↓
article_id = sha256(url)[:32]
    ↓
┌─────────────────────────────┐
│ <id>.html                   │ raw crawl
│ <id>.meta.json              │ crawl metadata
│ <id>.json                   │ normalized Article
└─────────────────────────────┘
```

## Decisions

- One stable `article_id` is derived from the canonical/discovered URL.
- The crawler writes raw HTML and a metadata sidecar using the same ID.
- The pipeline calculates the same ID and opens the exact HTML file.
- The pipeline no longer scans all HTML files and guesses which one belongs to a URL.
- Raw HTML is retained for future re-extraction.
- Normalized Article JSON is stored separately from crawl metadata.
- Crawl metadata includes source, requested URL, fetched URL, status, content type and fetch time.
- Missing crawls are skipped without killing the source.
- Extraction failures are isolated per article.
- No cross-source deduplication is introduced.

## Pool layout

```text
data/article_pool/
└── <source_id>/
    ├── <article_id>.html
    ├── <article_id>.meta.json
    └── <article_id>.json
```

## Next phase

Phase 6: EPUB generation from normalized Article records.
