# Phase 13 — Bounded page discovery + daily filtering

- Source URL is the crawl boundary.
- `https://vnexpress.net` → inspect only homepage.
- `https://vnexpress.net/chu-de/thanh-pho-ha-noi-2056` → inspect only that topic page.
- Maximum 20 article URLs; no RSS, sitemap, pagination or recursive crawl.
- Article with `published_at` today → keep.
- Article older than today → drop.
- Missing/unparseable `published_at` → keep.
- Dropped old articles are NOT replaced by deeper crawling.
- Timezone: `Asia/Ho_Chi_Minh`.

VnExpress discovery keeps page order, with CSS selectors plus a `-<numeric-id>.html`
URL fallback so CSS changes do not immediately break discovery.
