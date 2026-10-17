# Tàng Thư News Crawler — Phase 6 Checkpoint

Date: 17 October 2026

## Goal

Turn the normalized Article Pool into a real daily EPUB:

```text
Article Pool
    ↓
EpubGenerator
    ↓
data/editions/0neNews.epub
```

## Implementation

- Uses `EbookLib` as the EPUB engine.
- Tàng Thư only assembles metadata, chapters, policy handling and edition structure.
- Output is a valid EPUB ZIP, not a custom EPUB implementation.
- One fixed output filename: `0neNews.epub`.
- Edition title defaults to `YOUR NEWS at 07:00`.
- Date uses `Asia/Ho_Chi_Minh`.

## Source policy

The generator applies the existing source policy:

- `metadata_only`: title/metadata/link only.
- `excerpt`: first 800 characters of extracted body.
- `full_article`: full extracted body.
- `licensed`: full extracted body.

Unknown policy values fall back to `excerpt`.

## EPUB structure

- Edition/title page
- One XHTML chapter per article
- EPUB navigation
- TOC/spine
- Original article link
- Article title, source, date and author when available

## Error boundary

Phase 6 does not add:

- Google Drive
- OPDS
- personalization
- user folders
- GitHub artifact upload

Those remain later phases.

## Tests

The phase includes a real EPUB test:

- checks ZIP/EPUB output exists
- checks `mimetype`
- checks article XHTML
- checks article content
- checks metadata-only policy

## Next

Phase 7 can connect the generated `0neNews.epub` to the distribution layer, beginning with local artifact handling before Google Drive/OPDS integration.
