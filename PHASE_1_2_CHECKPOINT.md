# Phase 1/2 Checkpoint — Source Discovery

## Completed

- Generic `SourceDiscovery`.
- RSS/Atom XML discovery.
- VnExpress RSS index discovery.
- Sitemap XML discovery, including sitemap index recursion.
- HTML fallback discovery.
- URL normalization:
  - http/https only
  - same-host restriction
  - query/fragment removal
  - trailing slash normalization
  - duplicate removal
- Pipeline now prints the discovered Article URL Pool.

## VnExpress

The source configuration starts from:

`https://vnexpress.net`

RSS index:

`https://vnexpress.net/rss`

The RSS page currently publishes multiple VnExpress feeds, including "Tin mới nhất", "Tin nổi bật", and category feeds.

## Important boundary

This phase discovers URLs only.

Not implemented yet:
- Scrapy crawling
- article extraction
- newspaper4k
- Article Pool persistence
- EPUB
- Google Drive
- OPDS

## Next

Integrate Scrapy as the crawl engine and feed the normalized Article URL Pool into it.
