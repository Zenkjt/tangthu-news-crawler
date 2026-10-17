# PHASE 12 — Vietnamese News Discovery Architecture

## Decision
Tàng Thư không phụ thuộc RSS để tìm bài báo Việt Nam.

Discovery chính chuyển sang mô hình đã được nhiều crawler Việt Nam sử dụng:
- duyệt category;
- phân trang dạng `/category-p1`, `/category-p2`, ...;
- lấy link bài từ selector đặc thù của từng báo;
- canonicalize + deduplicate URL;
- Scrapy tiếp tục là engine tải bài;
- newspaper4k tiếp tục là extractor mặc định.

## VnExpress
Dùng:
- category pagination;
- selector `a.title-news`;
- 11 nhóm category;
- 1 page/category cho edition hiện tại;
- `max_urls: 300`.

RSS chỉ được giữ như khả năng fallback của framework, không phải dependency.

## Căn cứ
Các crawler Việt Nam trên GitHub thực tế dùng chính mô hình này cho VnExpress:
- `phanngoc/crawler`: duyệt `/{category}-p{page}`;
- `egliette/VNNewsCrawler`: dùng `title-news` để lấy article URL và selector riêng cho nội dung;
- `trungngv/web_scraping`: crawl VnExpress theo category và các page đánh số.

## Mục tiêu
Không viết lại một crawler tổng quát kiểu RSS-first. Tàng Thư dùng source-aware adapters/config cho đặc thù từng báo Việt Nam, nhưng giữ Scrapy + newspaper4k ở tầng dùng chung.

Next:
1. Test GitHub Actions.
2. Kiểm tra log phải có `vnexpress: discovered > 0 article URLs`.
3. Kiểm tra EPUB có bài thật.
