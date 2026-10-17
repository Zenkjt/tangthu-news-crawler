# Phase 9 TOC Checkpoint — Source → Article hierarchy

## Quyết định

EPUB có **TOC đầy đủ**, gồm:

- một trang `Mục lục` nằm trong nội dung EPUB;
- native EPUB navigation (`nav.xhtml` + NCX);
- mỗi nguồn tin là **một tầng hierarchy duy nhất**;
- bên dưới nguồn là các bài viết của nguồn đó;
- không tạo tầng category/subcategory.

Ví dụ:

MỤC LỤC
- VnExpress
  - Bài 1
  - Bài 2
- Tuổi Trẻ
  - Bài 3
  - Bài 4

## Navigation

Mỗi bài trong TOC liên kết trực tiếp tới XHTML tương ứng.

Cả TOC hiển thị trong nội dung và TOC native của EPUB đều được tạo.

## Trạng thái

Phase 9 — TOC update, chờ GitHub Actions xanh.
