# Phase 27 — Selector regression fix + image compression

## 1. Discovery fix

`page_articles` is now strictly selector-first. It only returns URLs matched by
its configured `article_link_selectors`; it no longer falls through to generic
HTML link scoring. This prevents unrelated links such as `/tac-gia/...` from
entering a VnExpress edition.

Generic discovery remains available through `strategy: generic` for sources
that need it (CNN/BBC and similar pages).

## 2. Image size

Article and cover images are normalized to:
- 480 × 800 px
- grayscale
- JPEG baseline (`progressive=False`)
- quality 70
- optimized JPEG encoding
- landscape images center-cropped to the 480:800 portrait ratio

The EPUB still keeps at most one main image per article. Text articles are not
dropped just to satisfy an EPUB size limit.

## Expected result

- The failing `test_vnexpress_selector_first_ignores_author_links` regression is
  resolved.
- EPUB image payload should be substantially smaller than the previous quality-88
  output while remaining compatible with CrossPoint's JPEG requirements.
