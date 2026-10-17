# Phase 22 — XHTML entity rendering fix

## Problem
Phase 21 already decoded HTML entities in the extractor, but the EPUB
generator escaped article text again with `html.escape()`. That converted
normal quotes/apostrophes into `&quot;` / `&#x27;`, and the e-reader displayed
those entities literally.

## Fix
- Article text nodes now use `html.escape(..., quote=False)`.
- The body is no longer escaped once before being escaped again per line.
- URL attributes continue to use normal attribute escaping.

## Expected result
The EPUB reader should display:
- `"` instead of `&quot;`
- `'` instead of `&#x27;`
- `&`, `<`, `>` safely escaped where required by XHTML.

## Scope
This is a replacement for:
`src/tangthu_crawler/epub.py`

No change to the crawler/extractor is required for this specific bug.

## Status
Ready to replace, commit, and run GitHub Actions.
