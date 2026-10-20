# CHECKPOINT — News On-demand Auto Dispatch — 2026-10-20

## Decision

On-demand must run automatically after a successful news subscription registration/update.

Flow:

    News UI
      -> News Worker
      -> commit config_news_subscriptions.json
      -> repository_dispatch
      -> tangthu-news-crawler
      -> on-demand(branch_id)
      -> ArticleCache / Crawl Planner
      -> build 0neNews.epub
      -> Google Drive

## Trigger contract

GitHub Actions event:

    repository_dispatch
    type: news-subscription-changed

Payload:

    {
      "mode": "on-demand",
      "branch_id": "<changed branch id>"
    }

## Dispatch rules

- `/news/register`: dispatch only when the resulting branch has active subscriptions.
- `/subscription/update` with `save`: dispatch the changed branch.
- `/subscription/update` with `cancel`: do not dispatch.
- `/source/add`: do not dispatch. Adding a source to the Bulletin Registry alone does not mean a shelf subscribed to it.
- Cancelling all subscriptions through the registration UI produces no dispatch because the selected subscription list is empty.
- The crawler workflow keeps the existing concurrency group, so a simultaneous Daily run is queued rather than duplicated.

## Authentication

The Worker calls GitHub `POST /repos/Zenkjt/tangthu-news-crawler/dispatches`.

This uses the existing Worker `GITHUB_TOKEN`; no Actions permission is required for this `repository_dispatch` design. The token needs repository Contents write access to the crawler repository.

## Files

- `src/index.js` — adds crawler dispatch after successful subscription changes.
- `.github/workflows/crawler.yml` — accepts `repository_dispatch` and maps its payload to `on-demand`.

## Verification

1. Replace both files and commit.
2. Wait for News Worker deployment.
3. Register or change one subscription from the News UI.
4. Verify a new `Tang Thu News Crawler` Actions run starts automatically.
5. Verify the run shows `on-demand` with the changed `branch_id`.
6. Verify cache-only / selective crawl behavior remains unchanged.
