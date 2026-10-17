# Tàng Thư News Crawler — Phase 4 Checkpoint

Date: 17 October 2026

## Fix

newspaper4k does not provide `Article.set_html()`.

The correct API for parsing already-downloaded HTML is `Article(input_html=...)`.
This is also the mechanism exposed by newspaper4k's CLI for parsing HTML from a file.

Therefore the extractor now:

```text
Scrapy
  ↓
raw HTML
  ↓
Article(input_html=raw_html)
  ↓
article.parse()
  ↓
normalized Article
```

No second HTTP request is made.

## Test status

The two failing extractor tests are fixed:

- core article fields
- missing publication date

The missing-date test now actually removes the date metadata instead of testing a fixture that contains a date.

## Reference

newspaper4k documentation confirms `input_html` is used for parsing supplied HTML without downloading it.
