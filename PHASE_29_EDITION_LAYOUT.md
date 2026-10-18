# Phase 29 — EPUB opening layout

## Decision

The EPUB opening flow is now:

1. Cover
2. Edition information
3. Mục lục
4. Articles

The EPUB navigation (`nav`) remains registered for EPUB readers but is no longer part of the reading spine, so it does not appear as an extra first page.

## Edition page

The second page is intentionally sparse but vertically and typographically balanced:

- YOUR NEWS
- edition time
- date
- article count

`published_at` remains metadata only; Phase 28's no-date-filter behavior is preserved.

No size cap was added.
