# Phase 26 — Generic HTML discovery + BBC Vietnamese + EPUB size cap

## Decisions

1. Discovery is now generic by default: collect internal HTML links and score article-likeness.
2. Source-specific URL regexes remain optional for sources that genuinely need them, but CNN is no longer the architectural model.
3. BBC Vietnamese topic page is added as the next cross-source test:
   `https://www.bbc.com/vietnamese/topics/cnlv9j1ekq0t`
4. BBC test policy is `excerpt` because the content is copyrighted.
5. Daily EPUB has a default hard size budget of **1.5 MiB (1,572,864 bytes)**. The generator keeps reducing the edition until it fits or only one article remains.

## Why the size cap

A 20-article VnExpress edition has already reached about 1.4 MB in practice. Images are normalized to 480x800 grayscale JPEG, so the edition size is driven mainly by the number of embedded article images plus XHTML/text. A 1.5 MiB cap keeps the e-reader edition compact while preserving the newest articles first.

## Important implementation note

The current size-cap loop is deliberately conservative and rebuilds the EPUB after dropping one article at a time. This is acceptable at the current 5–25 article scale. It can later be optimized with an estimated image-size budget if needed.

## Regression expectation

- VnExpress discovery remains selector-first and should still return up to 20.
- CNN can use the generic discovery engine instead of requiring a source-specific selector.
- BBC uses generic discovery.
