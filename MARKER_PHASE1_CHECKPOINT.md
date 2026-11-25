# Source Marker — Phase 1 checkpoint

Date: 2026-11-25
Repository: `Zenkjt/tangthu-news-crawler`

## Scope

Build the persistent Marker registry and assign one initial Marker to every source currently enabled in `Zenkjt/tangthu-opds/config/config_news_sources.json`.

This phase does **not** implement Analyzer, adapter scoring, fallback candidates, or automatic adapter switching. Initial records are deliberately `pending` until Analyzer verifies them.

## Design decisions

- Marker identity is `source_id`, not domain. Multiple URLs on the same domain can have independent discovery profiles.
- Registry file: `config/source_markers.json`.
- Schema version: `1`.
- Each Marker stores source URL/domain, selected adapter ID/version, discovery/extraction profile, status, quality fields, analysis metadata, marker version, and timestamps.
- Initial adapter assignment copies the currently configured behavior:
  - `vnexpress`: existing VnExpress adapter and its current per-URL profile.
  - `generic_html`: existing generic HTML discovery path.
- Initial status for every source is `pending`; no initial profile is represented as Analyzer-verified.
- `ensure_sources()` is idempotent and never overwrites an existing Marker. This protects later Analyzer decisions from being reset during normal runs.
- `update()` is the controlled write path for Analyzer results and validates status/adapter IDs.

## Initial source assignment

| source_id | URL | Initial adapter | Status |
|---|---|---|---|
| `s-d18f41563365` | `https://vnexpress.net/` | `vnexpress` | pending |
| `s-dc670b803afb` | `https://vnexpress.net/chu-de/thanh-pho-ha-noi-2056` | `vnexpress` | pending |
| `s-9be786efe3f7` | `https://vanhoanghethuat.vn/van-hoa` | `generic_html` | pending |
| `s-b1540afe5a40` | `https://vanhoanghethuat.vn/nghe-thuat` | `generic_html` | pending |
| `s-be033261cd1d` | `https://baomoi.com/the-gioi.epi` | `generic_html` | pending |
| `s-abf1949433a3` | `https://time.com/` | `generic_html` | pending |
| `s-c856fab26972` | `https://vanhoanghethuat.vn/du-lich` | `generic_html` | pending |
| `s-6ccd3104e718` | `https://znews.vn/sach-hay.html` | `generic_html` | pending |
| `s-9bc4d0fa3068` | `https://redsvn.net/category/nghe-thuat` | `generic_html` | pending |
| `s-b8e07db8d0c2` | `https://tinhte.vn/` | `generic_html` | pending |
| `s-e1cb35c2bd57` | `https://vnexpress.net/goc-nhin` | `vnexpress` | pending |

## Files

- `src/tangthu_crawler/marker.py`: Marker registry, initial assignment, apply, and Analyzer update API.
- `config/source_markers.json`: initial Marker records for all 11 enabled sources.
- `tests/test_marker.py`: idempotency, per-URL isolation, application, and update tests.

## Next step

Integrate Marker loading/application into the pipeline so every resolved source is assigned its Marker before discovery. Then build Analyzer to verify the initial assignments and update Marker status/profile. Do not add a fallback-adapter list.
