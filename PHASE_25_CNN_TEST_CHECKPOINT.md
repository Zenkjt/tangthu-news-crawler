# Phase 25 — CNN HTML discovery test + new cover

## Cover

Use the newly supplied cover image. It is normalized to:
- 480 × 800 px
- grayscale (`L`)
- baseline JPEG
- non-progressive
- center crop to the required 0.6 portrait ratio before resize

## CNN test

Added `config/sources/cnn.yaml` for a **test crawl of `https://www.cnn.com/`**.

Discovery remains **HTML-only**: no RSS, Atom, sitemap, or recursive crawl.
The page is bounded to 20 article URLs.

CNN article URLs use a configurable date-based regex instead of the VnExpress
`-123456.html` rule. This keeps the crawler generic.

Extraction uses `newspaper4k` first, with the existing quality gate.
Because CNN content is copyrighted, the test source is configured as
`policy.mode: excerpt`; full-text redistribution requires permission/licensing.

## Important test limitation

CNN blocks direct fetching in the current web research environment, so the
CNN live crawl has **not** been falsely marked successful here. The supplied
package is ready for the GitHub Actions runner, which is the actual crawler
environment.
