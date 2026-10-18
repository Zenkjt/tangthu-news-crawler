# Phase 28 — Bỏ lọc published_at

## Quyết định
Tàng Thư News không còn dùng `published_at` để quyết định bài có được đưa vào bản tin hay không.

Mỗi source lấy đúng số URL đã discovery, mặc định tối đa 20 bài (`max_articles: 20`).

## Logic mới

```text
Source page
  ↓
discovery
  ↓
20 article URLs
  ↓
Scrapy crawl
  ↓
extraction + quality gate
  ↓
đưa vào EPUB
```

- Không còn so sánh với ngày hiện tại.
- Không còn `dropped_old`.
- `published_at` vẫn được giữ trong metadata của bài nếu extractor lấy được, nhưng **không ảnh hưởng việc chọn bài**.
- Quality gate vẫn hoạt động: bài không đủ chất lượng vẫn bị loại.

## Lý do
Các nguồn CNN/BBC có metadata ngày khác nhau và việc lọc theo ngày làm mất các bài vừa discovery được. Với mô hình Tàng Thư hiện tại, discovery đã giới hạn 20 bài/source nên lấy đúng 20 bài là đơn giản, ổn định và phù hợp hơn.

## Size cap
Chưa áp dụng size cap. Trước tiên quan sát kích thước EPUB thực tế sau khi ảnh được chuẩn hóa 480×800 grayscale JPEG.
