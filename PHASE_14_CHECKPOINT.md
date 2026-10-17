# Tàng Thư News Crawler — Phase 14 Checkpoint

## Mục tiêu

Sửa discovery VnExpress sau khi test local xác nhận HTTP/HTML hoạt động bình thường.

## Kết quả local probe

- HTTP 200
- HTML ~265 KB
- `.title-news a`: 25 links
- `article h3 a`: 25 links
- URL-pattern: 28 candidates

Vì vậy framework `requests + BeautifulSoup` hoạt động; lỗi không nằm ở HTTP.

## Quyết định

Giữ framework hiện tại.

Với `page_articles`:

1. Fetch đúng URL nguồn.
2. Dùng selector của nguồn làm discovery chính.
3. VnExpress ưu tiên `.title-news a`, `article h3 a`, `article h2 a`.
4. Chỉ dùng URL-pattern scan như fallback.
5. Lọc các URL không phải bài viết như `/tac-gia/`, `/author/`, `/chu-de/`, `/video/`.
6. Tối đa 20 bài.
7. Không pagination.
8. Không recursive crawl.
9. Không RSS/sitemap cho mode này.

## Phạm vi

Chỉ sửa discovery. Không thay đổi EPUB, Drive upload hoặc pipeline ngày hôm nay.

## Test

Bổ sung test mô phỏng đúng cấu trúc VnExpress thực tế và bảo đảm URL tác giả không bị nhận nhầm thành bài viết.
