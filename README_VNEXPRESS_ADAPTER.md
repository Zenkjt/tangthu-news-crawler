# VnExpress Topic Adapter — patch bundle

## Included files

- `src/tangthu_crawler/vnexpress_adapter.py` — shared VnExpress homepage/topic discovery adapter.
- `src/tangthu_crawler/discovery.py` — complete replacement; routes `site_adapter: vnexpress` to the adapter and normalizes same-site subdomains.
- `config/sources/vnexpress.yaml` — enables the adapter and configures bounded discovery.
- `tests/test_vnexpress_adapter.py` — offline tests for article filtering, topic pagination, deduplication, limits, and per-URL start behavior.
- `CHECKPOINT_VNEXPRESS_TOPIC_ADAPTER_2026-11-18.md` — implementation checkpoint and outstanding validation.

## Intended behavior

- One `vnexpress` site adapter is reused for VnExpress URLs.
- Each registered source URL remains the starting URL for its own discovery run.
- Article links must match VnExpress's slug-plus-numeric-ID `.html` shape.
- Pagination follows only same-topic page links (`-pN`, `/pN`, `/page/N`, or `page/p` query) and never switches to a sibling topic.
- Page count and article count are bounded.
- Article URLs are deduplicated within the source only.
- If no trustworthy next-page link is present, discovery stops rather than guessing a URL.

## Apply through GitHub web

Create a feature branch first, then add/replace the files at the exact paths above. Do not commit directly to `main`.

## Validation

Run:

```bash
pip install -e ".[dev]"
pytest
```

The new adapter tests are offline and use deterministic HTML fixtures. A separate live smoke test against VnExpress is still required before marking a profile `verified`.

## Important scope boundary

This patch implements the site adapter only. It does not implement Source Analyzer, central Source Profile Registry, automatic quality scoring, or profile versioning. Those remain subsequent phases in `CHECKPOINT_Source_Auto_Profiling_TangThu_2026-11-17.md`.
