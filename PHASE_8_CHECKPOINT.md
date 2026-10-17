# PHASE 8 CHECKPOINT — EPUB CONTENT HARDENING

## Status
Phase 8 implementation ready to commit.

## Changes

### 1. Embedded article images
If normalized article data contains `image`, the generator attempts to download it and embeds it directly in the EPUB.

The EPUB therefore does not depend on the source website remaining available after download.

### 2. Image failure isolation
An unavailable or invalid image is ignored. The article remains in the EPUB without an image.

An image failure cannot abort the whole edition.

### 3. EPUB metadata
The book now includes:
- title
- Vietnamese language
- author: Tàng Thư
- publisher: Tàng Thư
- description

### 4. Article presentation
Each article contains:
- title
- source
- publication date
- author when available
- embedded image when available
- article body
- original article link

### 5. Existing policy remains unchanged
`metadata_only`, `excerpt`, `full_article`, and `licensed` continue to control article body redistribution.

### 6. Article Pool remains persistent
The Article Pool is still the durable cache. The edition only uses article IDs from the current run.

## Not implemented yet
- Drive upload/overwrite
- per-user editions
- OPDS integration
- advanced EPUB CSS/theme
- image resizing/optimization
