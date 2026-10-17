# Tàng Thư News Crawler — Phase 18 checkpoint

## Quyết định

Bỏ RSS/Atom khỏi pipeline discovery.

Lý do: máy đọc sách của Tàng Thư không có browser; link bài gốc trong EPUB không tạo ra giá trị sử dụng. RSS/Atom chỉ nên được xem là nguồn discovery, không phải nguồn nội dung full article.

## Discovery

- Chỉ discovery từ trang URL người dùng cấu hình.
- Vẫn giới hạn tối đa 20 article URL.
- Không pagination/recursive crawl.

## Article download

- Scrapy vẫn tải trực tiếp HTML của từng article URL.
- Giữ cấu hình Phase 16: 1 request/domain, delay 2s, AutoThrottle, retry.

## Article extraction

- Generic source: tiếp tục dùng newspaper4k.
- VnExpress: dùng source-specific extractor.
- VnExpress lấy nội dung trực tiếp từ `article.fck_detail` / `.fck_detail`.
- Thu thập `p`, `h2`, `h3`, `blockquote`, `figcaption` để giữ toàn bộ phần thân bài.
- Nếu `.fck_detail` không tồn tại hoặc rỗng thì article bị đánh dấu extraction failure, không âm thầm tạo EPUB thiếu nội dung.

## Mục tiêu

EPUB phải chứa toàn văn bài báo mà HTML của nguồn cung cấp, thay vì phần text bị newspaper4k cắt ngắn.
