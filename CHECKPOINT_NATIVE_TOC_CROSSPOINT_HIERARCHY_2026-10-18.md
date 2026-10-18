# Tàng Thư — Checkpoint: Native TOC theo kiến trúc CrossPoint

**Ngày:** 18 October 2026  
**Base:** `25f572db9ecd1439e0bb070d314e0836a271deb8`

## Kết quả nghiên cứu

CrossPoint hiện **đọc và giữ hierarchy của NCX**.

`TocNcxParser` tăng `currentDepth` khi gặp `navPoint` lồng nhau và ghi depth vào `TocEntry.level`. `EpubReaderChapterSelectionActivity` sau đó dùng `tocItem.level` để tạo indent:

- level 1 → không indent
- level 2 → indent 2 spaces

Vì vậy TOC đúng cho Tàng Thư là:

```text
Nguồn A
  Bài A1
  Bài A2
  Bài A3

Nguồn B
  Bài B1
  Bài B2
```

## Hành vi

- `Nguồn A` là parent `navPoint`.
- `Nguồn A` trỏ tới `article-A1.xhtml`.
- Chọn `Nguồn A` → nhảy ngay tới bài đầu tiên của nguồn A.
- Các bài của nguồn được hiển thị thụt vào.
- `toc.xhtml` touch vẫn giữ Source → Article.
- Không thay đổi crawler, extraction, dedup hay ArticlePool.

## Bỏ quyết định cũ

Quyết định trước đây rằng native TOC phải flat là **không còn phù hợp với CrossPoint hiện tại**. CrossPoint source hiện tại đã hỗ trợ hierarchy và UI `Select Chapter` sử dụng `level`.

## Code model

EbookLib native TOC dùng dạng:

```python
(
    epub.Link("article-1.xhtml", "Nguồn A", "source-1"),
    (
        epub.Link("article-1.xhtml", "Bài A1", "article-1"),
        epub.Link("article-2.xhtml", "Bài A2", "article-2"),
    ),
)
```

EbookLib sinh parent/child `navPoint` trong NCX.
