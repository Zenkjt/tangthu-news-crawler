# Tàng Thư News Crawler — Phase 19 Checkpoint

## Decision

RSS/Atom is removed from the news pipeline. Discovery uses the configured source page and returns at most 20 article URLs.

## Problem fixed

Some VnExpress article templates do not expose the body as `.fck_detail` directly. Phase 18 therefore dropped otherwise valid articles.

## Extraction strategy

VnExpress extraction now checks, in order:

1. `article.fck_detail`
2. `#article_content.fck_detail`
3. `#article_content`
4. `article.content_detail`
5. `.content_detail.fck_detail`
6. `.main_content_detail`

The first candidate containing actual article content is used. `newspaper4k` remains the generic extractor for other sources.

## Unchanged

- HTML discovery: maximum 20 URLs.
- Scrapy downloader and Phase 16 rate limiting.
- Today/undated filtering.
- EPUB generation and Drive in-place update.
- Source-specific adapter architecture.

## Validation

Added a regression test for the `content_detail` fallback.
