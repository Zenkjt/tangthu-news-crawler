# Phase 31 — Giảm dung lượng ảnh và chốt mô hình edition

## Thay đổi thực hiện

- Giữ ảnh bài báo ở `480×800`, grayscale, baseline JPEG.
- Giảm JPEG quality của **ảnh bài báo** từ `70` xuống `45`, vẫn `optimize=True`, `subsampling=2`.
- Giữ cover riêng, không hạ chất lượng cover theo thay đổi này.
- Ép thứ tự article theo **thứ tự source trong registry**, sau đó theo thứ tự discovery. Điều này ngăn một source xuất hiện lại ở giữa TOC nếu ArticlePool có record cũ.
- Chưa áp size cap.

## Chốt kiến trúc edition cho bước sau

Hai chế độ:

1. `text_only`
   - Mỗi source: `5–25` bài.
   - Tổng edition: tối đa `150` bài.
   - Không tải/nhúng ảnh bài báo.

2. `text_and_pic`
   - Mỗi source: `5–25` bài.
   - Tổng edition: tối đa `100` bài.
   - Tải và chuẩn hóa ảnh bài báo.

Giới hạn tổng là giới hạn cứng; giới hạn từng source vẫn do người dùng chọn trong khoảng 5–25.

`published_at` chỉ là metadata, không tham gia chọn/sắp xếp bài.

## Chính sách nội dung

`text_only` và `text_and_pic` chỉ là **chế độ trình bày/số lượng**. Chúng không ghi đè `policy.mode` của từng source. Source `excerpt` vẫn chỉ được đưa excerpt; `full_article`/`licensed` mới đưa toàn văn.
