# PHASE 7 CHECKPOINT — EDITION PIPELINE HARDENING

## Status
Phase 7 is ready to commit.

## Problem fixed
The Article Pool is persistent. If the EPUB generator scans the whole pool, old articles from previous runs would appear in today's edition.

The pipeline now tracks `edition_article_ids` during the current crawl/extraction run and passes only those IDs to the EPUB generator.

This preserves the Article Pool as a reusable cache while keeping each daily edition fresh.

## Source isolation
A failure in one source no longer aborts the complete edition:

- discovery failure -> skip source
- crawl failure -> skip source
- extraction failure -> skip individual article

Other active sources continue processing.

## EPUB behavior
`EpubGenerator.generate()` now accepts:

```python
article_ids: set[str] | None = None
```

- `None`: include all matching Article Pool articles.
- set of IDs: include only selected articles.
- empty set: generate a valid edition containing only the edition page.

## Architecture
```text
Source 1 ──┐
Source 2 ──┼─> crawl/extract ─> current-run article IDs ─> EPUB
Source 3 ──┘
                         │
                         └──> persistent Article Pool
```

## Important decision
Do NOT delete the Article Pool after generating the EPUB. It is the durable extraction cache and allows later reprocessing without crawling again.

## Not yet implemented
- image assets inside EPUB
- Google Drive upload/overwrite
- per-user editions
- OPDS distribution
