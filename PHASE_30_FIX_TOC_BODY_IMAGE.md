# Phase 30 — Fix TOC order, article policy, and image size

## Findings

1. **TOC bị xáo trộn**: `EpubGenerator` đang sort article theo `published_at`. Điều này làm các bài của cùng source bị chen giữa các source. Pipeline cũng dùng `set`, nên thứ tự discovery bị mất.
2. **Bài CNN/BBC bị cắt**: đây là do source policy đang đặt `mode: excerpt`, không phải do Scrapy/extractor. Phase 30 không đổi policy bản quyền. VnExpress vẫn `full_article`.
3. **Ảnh EPUB lớn**: JPEG đang dùng quality 88, `optimize=False`, `subsampling=0`. Phase 30 đổi article images sang grayscale baseline JPEG 480×800, quality 70, optimize=True, subsampling=2.

## Chốt

- Giữ nguyên thứ tự discovery: source 1 → tối đa 20 bài, source 2 → tối đa 20 bài, source 3 → tối đa 20 bài.
- Không dùng `published_at` để sắp xếp edition.
- `published_at` chỉ là metadata.
- Không đổi chính sách excerpt của CNN/BBC.
- Chưa áp size cap.
