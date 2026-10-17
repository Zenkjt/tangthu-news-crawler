# Tàng Thư News Crawler — Phase 4 Checkpoint

Date: 17 October 2026

## Completed

Integrated newspaper4k as the default article extraction engine.

Pipeline:

```text
Discovery
    ↓
Scrapy
    ↓
raw HTML
    ↓
newspaper4k
    ↓
normalized Article
    ↓
Article Pool JSON
```

## Normalized fields

- `id`
- `source_id`
- `url`
- `canonical_url`
- `title`
- `author`
- `published_at`
- `body`
- `image`

## Decisions

- newspaper4k is the default extractor.
- Extraction runs after crawling, against stored raw HTML.
- Missing optional metadata does not fail extraction.
- Raw HTML is retained; normalized JSON is an additional representation.
- No EPUB generation yet.
- No Google Drive upload yet.
- No OPDS logic yet.
- Source-specific custom extractors remain a later fallback when newspaper4k quality is insufficient.

## Important implementation note

The current phase establishes the extraction interface and normalized Article shape.
Before production-scale crawling, the Article Pool should be tightened so each raw HTML file is mapped to its exact ArticleRef by URL hash rather than scanning source files.

## Next phase

Phase 5: Article Pool / dedup / persistence hardening, then EPUB generation.
