# Tàng Thư News Crawler

Crawler tạo bản tin EPUB cá nhân cho Tàng Thư.

## Hiện trạng
- Source Registry đọc cấu hình từ `config/sources/*.yaml`.
- Pipeline lập kế hoạch crawl, quản lý article cache và tạo EPUB theo từng branch.
- VnExpress có adapter riêng cho discovery và extraction.
- Có pytest và live smoke test cho VnExpress.
- EPUB được kiểm tra trước khi upload Google Drive.

## Kiểm thử
Yêu cầu Python 3.12 trở lên.

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## VnExpress live smoke test

```bash
python scripts/vnexpress_live_smoke.py --url "https://vnexpress.net/goc-nhin" --max-articles 25 --max-pages 1
python scripts/vnexpress_live_smoke.py --url "https://vnexpress.net/thoi-su/ha-noi-today" --max-articles 25 --max-pages 1
```

Workflow live test chạy khi có thay đổi liên quan trên `main` hoặc được kích hoạt thủ công. Đây là kiểm tra phụ thuộc website bên ngoài; pytest là bộ kiểm thử ổn định chính.

## Cấu trúc
- `config/sources/`: cấu hình nguồn.
- `src/tangthu_crawler/`: discovery, adapters, extraction, cache, planner, EPUB và pipeline.
- `scripts/`: công cụ kiểm tra.
- `tests/`: kiểm thử và fixtures.
- `.github/workflows/`: GitHub Actions.

## Nguyên tắc
- Ưu tiên adapter riêng khi website có cấu trúc đặc thù.
- Chỉ đưa bài đạt quality gate vào cache và EPUB.
- Không commit dữ liệu chạy, cache, bytecode hoặc môi trường Python.
