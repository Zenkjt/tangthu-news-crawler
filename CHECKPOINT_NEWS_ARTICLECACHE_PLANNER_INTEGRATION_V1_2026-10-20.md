# CHECKPOINT — ArticleCache + Crawl Planner integration v1
Date: 2026-10-20

## Implemented in this package
- Pipeline reads branches, sources, and subscriptions from the News Worker `/news/config`.
- Only active subscriptions and enabled sources/branches are eligible.
- Local `config/sources/*.yaml` extractor/discovery settings are mapped to Bulletin Registry IDs by normalized URL/host.
- Unknown hosts use generic HTML discovery + newspaper4k and excerpt policy by default.
- Crawl Planner is connected to ArticleCache. On-demand considers only one `branch_id`; daily plans one crawl per unique subscribed source.
- ArticleCache stores qualified normalized content with `fetched_at` from Scrapy metadata; TTL stays exactly 5 days from that moment.
- Expired cache cleanup runs before and after crawling.
- Per-branch EPUBs are composed from selected cached articles. Local files are `<branch_id>-0neNews.epub`; upload target in each Drive root is `0neNews.epub`.
- If a branch has no active subscriptions, the job does not crawl, build, upload, or delete its old file.
- Workflow schedule changed to 06:45 Asia/Ho_Chi_Minh (`45 23 * * *` UTC).
- Workflow has `workflow_dispatch` inputs `mode` (`daily` / `on-demand`) and `branch_id`.
- Cache JSON is persisted back into this repo after successful crawl; workflow requests `contents: write`.

## Important behavior
- Daily: active subscriptions -> unique sources -> one crawl decision/source -> update cache -> build each active branch edition.
- On-demand: changed branch only -> cache sufficiency check -> crawl only source(s) whose valid cache is insufficient -> build that branch.
- Selection inside a source uses discovery/fetch timestamps rather than `published_at`.
- `text` edition maximum: 200 articles. `images` edition maximum: 100.
- No cross-source deduplication.

## Remaining integration step
The Worker does not yet dispatch GitHub Actions after registration/subscription updates. Until that trigger bridge is added, on-demand mode can be run manually from Actions by selecting `mode=on-demand` and entering the changed `branch_id`.

## GitHub connector note
At the time of preparing this package, writing to the repository through the connected GitHub integration returned HTTP 403 `Resource not accessible by integration`; these files must be copied/committed by the repository owner.
