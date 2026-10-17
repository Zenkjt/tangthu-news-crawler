# Tàng Thư News Crawler — Phase 21

## Problem

Some VnExpress article text appeared in EPUB as HTML entities such as:

- `&quot;`
- `&#x27;`

The HTML had been entity-encoded more than once, so BeautifulSoup decoded only
one layer and the remaining entity text reached the EPUB.

## Fix

Added a shared `_clean_text()` normalization step using `html.unescape()` twice
and whitespace normalization.

Applied to:
- generic newspaper4k title/body
- VnExpress title/body/description/author
- VnExpress candidate scoring text

This is deliberately a generic text-normalization layer, not a VnExpress-only
hack.

## Validation

Added a regression test for double-encoded `&quot;` and `&#x27;`.

## Scope

This phase fixes text entity rendering.

The separate issues of:
- image preservation/embedding
- false discovery of hashtag/category pages

remain separate and should be handled next after confirming this phase.
