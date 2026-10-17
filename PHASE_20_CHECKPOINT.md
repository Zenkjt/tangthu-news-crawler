# Tàng Thư News Crawler — Phase 20

## VnExpress

VnExpress now uses a source-specific extractor with a content-density
fallback instead of adding selectors indefinitely.

Candidate containers:
- known VnExpress article containers
- generic `article`
- generic `main`

Candidates are scored by:
- text length
- paragraph count
- link-text ratio

The highest-quality candidate is selected, then article blocks are extracted
from paragraphs/headings/quotes/captions.

## Policy

VnExpress is set to `full_article`.

## Multi-source architecture

Other newspapers should NOT reuse VnExpress selectors.

The generic architecture is:

1. source-specific adapter when a source has a known structure;
2. generic newspaper4k extraction for unknown sources;
3. generic DOM/content-density fallback for sources where the generic
   extractor returns empty or suspiciously short content;
4. quality gate before EPUB generation;
5. source policy decides metadata/excerpt/full_article/licensed output.

Thus the crawler engine stays common while source-specific differences remain
isolated in adapters.

## Next validation

Run GitHub Actions and expect the two previously failing VnExpress URLs to
extract successfully and `edition kept=20`.
