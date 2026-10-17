# Tàng Thư News Crawler — Phase 16 Checkpoint

## Mục tiêu

Xử lý lỗi VnExpress trả `429 Too Many Requests` khi Scrapy tải 20 article URLs sau khi discovery đã hoạt động đúng.

## Chẩn đoán

- Discovery homepage: HTTP 200.
- Discovery lấy đúng tối đa 20 article URLs.
- `async start()` đã sửa đúng cơ chế Scrapy mới; Scrapy thực sự bắt đầu crawl.
- Lỗi còn lại là tầng article downloader: nhiều request đồng thời khiến VnExpress trả 429.
- Một số URL trả 404 và vẫn được giữ là lỗi riêng của từng URL, không coi là lỗi discovery.

## Quyết định Phase 16

Giữ nguyên Scrapy + newspaper4k. Không thay kiến trúc.

Article downloader dùng cơ chế chuẩn của Scrapy:

- Browser-like `USER_AGENT`, giống discovery.
- `DEFAULT_REQUEST_HEADERS` giống discovery.
- `CONCURRENT_REQUESTS=1` mặc định.
- `CONCURRENT_REQUESTS_PER_DOMAIN=1`.
- `DOWNLOAD_DELAY=2` giây.
- `AUTOTHROTTLE_ENABLED=true`.
- AutoThrottle target concurrency = 0.5.
- Max delay = 10 giây.
- HTTP 429 tiếp tục đi qua RetryMiddleware.
- Retry tối đa 2 lần.

Không tăng số lượng URL để bù bài lỗi. Vẫn giữ boundary tối đa 20 bài từ chính trang nguồn.

## Luồng sau Phase 16

```text
Source URL
  ↓
Discovery
  ↓ max 20 URLs
Scrapy ArticleSpider
  ↓ 1 request/domain + delay + AutoThrottle
HTML article
  ↓
newspaper4k
  ↓
lọc published_at theo ngày
  ↓
EPUB
  ↓
Google Drive
```

## Tiêu chí kiểm tra

Actions phải cho thấy:

1. Discovery: `HTTP status=200` và `discovered 20 article URLs`.
2. Scrapy không còn `Crawled 0 pages`.
3. Tỷ lệ 429 giảm rõ rệt hoặc biến mất.
4. Có HTML/meta files trong Article Pool.
5. `edition kept` > 0 nếu các bài có ngày đăng hôm nay.
6. EPUB có nội dung.
7. Upload Drive vẫn `updated` file `0neNews.epub`.
