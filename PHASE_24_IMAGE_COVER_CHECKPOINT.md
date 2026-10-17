# Image compatibility + 0neNews cover checkpoint

## Chốt tương thích CrossPoint
- Article images and cover are embedded as JPEG baseline (not progressive).
- Each generated image is grayscale (`L` / 8-bit), exactly 480×800 px.
- `ImageOps.fit` uses center-crop to fill the portrait frame. Landscape images lose the left/right edges as necessary; aspect ratio is not distorted.
- JPEG encoder flags: `progressive=False`, `optimize=False`, `subsampling=0`.
- EPUB image manifest uses MIME `image/jpeg` and `.jpg` filenames.

## Cover
- Added `assets/0neNews-cover.jpg`, an original monochrome Tàng Thư / YOUR NEWS cover, 480×800, grayscale JPEG baseline.
- Cover manifest entry includes EPUB 3 `properties="cover-image"` and EPUB 2 `<meta name="cover" content="cover-image"/>` metadata.
- Added `cover.xhtml` as the first readable page in the spine.
- When the external cover asset is missing in another installation, a code-generated baseline JPEG cover is used as fallback.

## Change scope
- Replacement: `src/tangthu_crawler/epub.py`
- New asset: `assets/0neNews-cover.jpg`

## Verification needed
Run unit tests and one GitHub Actions edition build, then verify that both the cover and article images render on the physical CrossPoint/X4 device. Calibre rendering alone is not sufficient.
