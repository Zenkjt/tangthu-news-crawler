# CHECKPOINT — ArticleCache v2 — 2026-10-20

## Đã chốt

- Lifecycle mỗi article: **chính xác 5 ngày kể từ `fetched_at`**.
- Không dùng `published_at` để quyết định hết hạn.
- Không tự xoá article cũ chỉ vì source có tin mới hơn.
- Refresh cùng `(source_id, canonical_url)` sẽ cập nhật record và reset TTL 5 ngày theo `fetched_at` mới.
- Cache identity: `source_id + canonical_url`.
- Cùng URL nhưng khác source là hai record độc lập.
- `text`: article còn TTL là usable.
- `images`: article còn TTL và phải có cached image.
- Expired article không được dùng để build edition và được cleanup.

## Implementation

`src/tangthu_crawler/article_cache.py`

API: `upsert()`, `get()`, `valid_articles()`, `valid_count()`, `cleanup_expired()`, `all_records()`.

## Tests

Bao phủ upsert/get, update không duplicate, khác source độc lập, TTL đúng 5 ngày, refresh reset TTL, image mode và cleanup expired.

## Bước tiếp theo

Nối ArticleCache vào Crawl Planner v2 và pipeline crawler hiện tại.
