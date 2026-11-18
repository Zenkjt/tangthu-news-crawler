# CHECKPOINT — VnExpress Topic Adapter

**Ngày:** 18/11/2026  
**Repo:** `Zenkjt/tangthu-news-crawler`  
**Baseline:** nhánh mặc định `main`  
**Trạng thái:** Implementation bundle đã chuẩn bị; chưa được ghi vào repository.

## 1. Phạm vi

Triển khai adapter dùng chung cho VnExpress homepage và các URL nhánh/chuyên trang. URL đăng ký vẫn là điểm bắt đầu riêng của từng lần Discovery; adapter không tự chuyển sang nhánh chủ đề khác.

Không triển khai Source Analyzer, central Profile Registry, profile scoring/versioning hoặc feedback loop trong checkpoint này.

## 2. Phát hiện từ code hiện tại

- `src/tangthu_crawler/discovery.py` có `page_articles`, `category_pagination`, `selector`, RSS và Sitemap.
- `page_articles` chỉ đọc một trang, chưa xử lý phân trang.
- `pipeline.py::_resolve_sources()` fallback cấu hình theo hostname. Cấu hình VnExpress local được dùng chung khi source registry cung cấp URL VnExpress khác; `config["url"]` sau đó được thay bằng URL đăng ký.
- `config/sources/vnexpress.yaml` hiện mới khai báo trang chủ với `page_articles`.
- `extractor.py` đã có extractor riêng `engine: vnexpress`; không thay đổi extractor trong patch này.

## 3. Thay đổi đã chuẩn bị

1. Thêm `src/tangthu_crawler/vnexpress_adapter.py`.
   - Chọn link bài theo selector VnExpress.
   - Fallback chỉ khi URL khớp mẫu slug + numeric article ID `.html`.
   - Bỏ qua author/tag/video/podcast và external links.
   - Theo phân trang cùng topic bằng page suffix `-pN`, `/pN`, `/page/N` hoặc query `page/p`.
   - Giới hạn `max_pages` và `max_articles`.
   - Deduplicate URL trong cùng source.
   - Không tự suy đoán URL trang tiếp theo nếu HTML không cung cấp liên kết phân trang.

2. Sửa `src/tangthu_crawler/discovery.py`.
   - Route `site_adapter: vnexpress` sang adapter mới.
   - Cho phép hostname cùng site có/không có `www` trong bước normalize.
   - Giữ nguyên các strategy generic hiện có.

3. Cập nhật `config/sources/vnexpress.yaml`.
   - Khai báo `site_adapter: vnexpress`.
   - Bổ sung selector và giới hạn crawl.
   - Giữ nguyên `extractor.engine: vnexpress`, Quality Gate và policy hiện tại.

4. Thêm `tests/test_vnexpress_adapter.py` với 4 test offline.

## 4. Kiểm thử đã chạy

Trong môi trường kiểm thử tạm:

- 4 test mới của adapter: PASS.
- 6 test discovery hiện có được đối chiếu: PASS.
- Tổng cộng: **10 passed**.

Lưu ý: phần test discovery hiện có dùng stub cục bộ cho helper `_is_today_or_undated`; đây không phải full test suite của repository. Chưa chạy full `pytest` với toàn bộ dependency và code repository.

## 5. Chưa nghiệm thu production

Chưa có live smoke test trực tiếp từ runner GitHub Actions. Chưa xác nhận pagination DOM thực tế của mọi chuyên trang. Vì vậy không đánh dấu profile `verified` ở giai đoạn này.

Cần kiểm tra tối thiểu:

- `https://vnexpress.net/goc-nhin`
- `https://vnexpress.net/goc-nhin/kinh-doanh-quan-tri`
- `https://vnexpress.net/goc-nhin/van-hoa-loi-song`
- Một chuyên trang khác thuộc nhóm tin thời sự/công nghệ.

Tiêu chí: link đều thuộc đúng topic, không có author/tag/video, không lặp URL, phân trang không đi sang sibling topic, extraction đạt Quality Gate.

## 6. Trạng thái GitHub

Đã đọc được repository và code từ GitHub. Tuy nhiên thao tác tạo branch qua GitHub integration trả HTTP 403 `Resource not accessible by integration`. Không có branch, commit hoặc PR nào được tạo; `main` chưa bị thay đổi.

Sau khi quyền GitHub Contents write + Pull Requests write được cấp, áp dụng bundle trên feature branch và mở PR, không commit trực tiếp vào `main`.
