# Checkpoint — Generic Extraction chuyển sang Trafilatura

Ngày: 2026-10-21
Base: `222bc717511e740f20723cdb56c3b4b7a205c06c`

## Quyết định

Thay generic extraction dựa trên newspaper4k bằng Trafilatura 2.3.x.

- Scrapy giữ nguyên.
- HTML discovery giữ nguyên.
- VnExpress adapter giữ nguyên.
- Trafilatura là generic extraction engine mặc định.
- `favor_recall=True` để ưu tiên lấy đủ thân bài.
- `include_comments=False` để không kéo phần bình luận vào bài.
- `include_tables=True` để không bỏ bảng có ý nghĩa trong bài.
- Metadata lấy từ Trafilatura.
- Canonical/image vẫn normalize từ HTML hiện có để giữ schema Tàng Thư ổn định.
- newspaper4k chỉ còn là rescue engine khi Trafilatura trả body quá ngắn hoặc không trả document.
- Legacy DOM extractor chỉ còn là fallback cuối cùng của newspaper4k.

## Quality Gate

Giữ contract hiện tại: title, độ dài body và số paragraph. Không biến Quality Gate thành một extractor thứ hai.

## Không thay đổi

Discovery, Crawl, ArticleCache, EPUB, Drive upload, policy/copyright.

## Dependency

`trafilatura>=2.3,<3`

## Kiểm thử

Đã kiểm tra syntax của replacement `extractor.py` bằng `py_compile`.
Runtime integration test cần chạy trong môi trường có dependency `trafilatura` (môi trường dựng file hiện tại không có network để cài package).

## Source configuration decision

Không đóng gói BBC/CNN hay bất kỳ source YAML cụ thể nào trong bộ generic replacement. Source Registry hiện có của Tàng Thư nằm ngoài core crawler. Generic path mặc định dùng Trafilatura; adapter VnExpress chỉ là ngoại lệ tương thích hiện có.
