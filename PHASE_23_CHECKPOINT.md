# Phase 23 — Article filtering + 480×800 BMP images

## Chốt
Phase 23 xử lý **cả hai** vấn đề:
1. Lọc article nhận nhầm trang hashtag/danh mục sau discovery và sau khi fetch.
2. Tải ảnh bài viết, chuyển thành BMP grayscale 480×800 và nhúng vào EPUB.

## 1. Lọc article sai
### Discovery
VnExpress giữ quy tắc URL bài báo:
`/<slug>-<numeric_id>.html`

Thêm denylist source-specific cho các path không phải article:
- `/tag/`
- `/topic/`
- `/search/`
- `/tim-kiem/`
- `/category/`
- `/photo/`
- `/podcast/`
- `/live/`
- `/infographics/`
- `/video/`
- `/chu-de/`
- `/tac-gia/`
- `/author/`

### Quality gate sau extraction
VnExpress chỉ được đưa vào Article Pool/edition khi:
- có title;
- title không phải `Untitled` hoặc `Article`;
- body >= 300 ký tự;
- body có >= 2 đoạn.

Log mới:
`quality drop <url>: <reason>`

Edition log thêm `dropped_quality`.

## 2. Ảnh EPUB
Mỗi article có `image` URL thì:
- tải ảnh với browser-like User-Agent;
- timeout 15 giây;
- EXIF orientation được xử lý;
- giữ tỷ lệ, không crop;
- không upscale vượt kích thước nguồn;
- nền trắng;
- canvas chính xác **480×800 px**;
- grayscale 8-bit (`L`);
- BMP;
- nhúng vào EPUB dưới `images/article-N.bmp`.

Ảnh lỗi không làm fail cả article/edition.

## 3. Dependency
Thêm `Pillow>=10.0`.

## 4. Không thay đổi
- giới hạn discovery 20 bài;
- chỉ lấy bài trên trang nguồn đã cấu hình;
- full_article;
- xử lý HTML entities của Phase 22;
- Drive overwrite `0neNews.epub`;
- OPDS/Apps Script.

## 5. Expected result
Một trang hashtag/category không còn chiếm slot 20 bài ngay từ discovery; nếu một trang đặc biệt vẫn lọt qua URL filter, quality gate sẽ loại trước khi vào edition.

Ảnh bài báo có thể xuất hiện trong EPUB dưới dạng BMP 480×800 grayscale, phù hợp mục tiêu CrossPoint X4/mini e-reader.
