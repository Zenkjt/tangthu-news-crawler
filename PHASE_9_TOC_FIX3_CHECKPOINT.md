# Tàng Thư News Crawler — Phase 9 TOC Fix 3

## Fix
The test incorrectly required `Fixture News` to appear in `EPUB/nav.xhtml`.

EbookLib's generated EPUB 3 navigation page exposes the explicit `Mục lục`
link here, while the source → article hierarchy is represented by the EPUB
package TOC (`book.toc` / NCX) and the visible in-book `toc.xhtml`.

## Decision
Keep the intended two-level hierarchy:

Source
└── Article

The test now verifies `toc.xhtml` in `nav.xhtml` and separately verifies the
source hierarchy in the visible TOC.

## Result
No production EPUB hierarchy change was made; only the incorrect test
assumption was removed.
