# Tàng Thư News Crawler — Phase 6 Checkpoint

Date: 17 October 2026

## Status

Phase 6 implementation is complete. The first CI run exposed a test-only path mismatch: EbookLib stores XHTML under `EPUB/`, not `OEBPS/`. The generator itself successfully produced a valid EPUB.

## Final decision

Use EbookLib as the EPUB engine. Tàng Thư assembles the edition and applies source policy; it does not implement the EPUB container itself.

## Output

```text
data/editions/0neNews.epub
```

Fixed filename, ready for a later distribution phase.

## EPUB structure

EbookLib generates:

```text
mimetype
META-INF/container.xml
EPUB/content.opf
EPUB/nav.xhtml
EPUB/toc.ncx
EPUB/edition.xhtml
EPUB/article-1.xhtml
EPUB/article-2.xhtml
...
```

## Source policy

- `metadata_only`: metadata + original link, no article body.
- `excerpt`: first 800 characters.
- `full_article`: full extracted body.
- `licensed`: full extracted body.
- unknown mode: falls back to `excerpt`.

## CI result

Before fix:

- 10 tests passed
- 2 EPUB tests failed
- failure was caused by tests expecting `OEBPS/article-1.xhtml`
- actual EbookLib path is `EPUB/article-1.xhtml`

After fix, the tests should validate the actual EPUB layout.

## Not included yet

- Google Drive
- OPDS
- user personalization
- GitHub artifact upload
