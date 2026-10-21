# Tàng Thư — Pagination Full-Text Checkpoint

Date: 2026-10-21

## Decision

Bổ sung pagination handling ở **crawler + extractor**, không tạo adapter riêng cho Văn hóa Nghệ thuật.

## Behavior

1. Scrapy fetches page 1 as the normal article.
2. Crawler detects a continuation link when it looks like:
   - `rel="next"`
   - `Next`, `Next page`, `Trang 2`, numeric pagination
   - URL forms such as `-page2`, `-p2`, `/page/2`, `/2`, `?page=2`, `?p=2`.
3. Candidate must remain on the same domain and resolve to the same article identity.
4. Maximum pagination depth defaults to 5 pages.
5. All pages retain the same root article ID:
   - `HASH.html`
   - `HASH.page2.html`
   - `HASH.page3.html`
6. Extractor detects the sidecar pages and runs the existing extraction engine on each page.
7. Bodies are merged in page order and duplicate paragraphs are suppressed.
8. The EPUB receives **one Article**, not one Article per page.
9. The root URL/canonical identity remains the first page.

## Why this belongs in generic core

Pagination is a document-structure problem, not a Văn hóa Nghệ thuật-specific extraction rule. The implementation therefore stays generic and can handle other publishers using common pagination URL/HTML patterns.

## Scope

Changed:
- `src/tangthu_crawler/crawler.py`
- `src/tangthu_crawler/extractor.py`
- `tests/test_pagination.py`

No source-specific YAML or adapter is added.

## Validation

The test suite covers:
- Văn hóa Nghệ thuật-style `-page2.html`
- `?page=2`
- `/2`
- multi-page file discovery
- ordered body merge with duplicate suppression
