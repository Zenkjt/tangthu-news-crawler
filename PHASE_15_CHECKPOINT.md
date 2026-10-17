# Tàng Thư News Crawler — Phase 15 Checkpoint

## Mục tiêu

Xác định và xử lý lớp HTTP trước khi tiếp tục sửa discovery.

## Bằng chứng

GitHub Actions trả:

    page fetch failed https://vnexpress.net/ 404

Trong khi local browser-like request trả HTTP 200 và HTML có bài viết.

## Sửa

1. HTTP client dùng browser-like Chrome User-Agent mặc định.
2. Thêm Accept / Accept-Language / Accept-Encoding / Connection / Upgrade-Insecure-Requests.
3. VnExpress có Referer `https://vnexpress.net/`.
4. `_get()` in diagnostic:
   - status
   - final URL
   - Content-Type
   - bytes
   - Server
   - User-Agent
5. Không thay đổi logic giới hạn 20 bài.
6. Không thay đổi extractor, EPUB hoặc Drive upload.

## Mục tiêu của lần chạy này

Không cần kỳ vọng đã giải quyết hoàn toàn.

Log cần đọc là:

    HTTP status=...
    final_url=...
    content_type=...
    bytes=...
    server=...
    user_agent=...

Nếu vẫn 404 dù browser-like UA, vấn đề là response theo IP/GitHub runner hoặc chính sách phía VnExpress; lúc đó sẽ xử lý ở tầng fetch, không tiếp tục sửa selector.
