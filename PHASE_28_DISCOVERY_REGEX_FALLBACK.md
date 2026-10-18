# Phase 28 — Selector-first discovery regression fix

`page_articles` remains strict and does not fall back to generic link scoring.
If configured selectors find nothing, it uses only the narrow article URL regex fallback.
Image compression from Phase 27 is retained.
