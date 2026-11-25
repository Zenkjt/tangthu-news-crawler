# Apply Marker Phase 1 files

Copy these paths into the repository `Zenkjt/tangthu-news-crawler` using GitHub Web:

1. Add `src/tangthu_crawler/marker.py`.
2. Add `config/source_markers.json`.
3. Add `tests/test_marker.py`.
4. Add `MARKER_PHASE1_CHECKPOINT.md`.

Commit message: `news: add source marker registry and initial assignments`

All 11 current sources have a Marker with status `pending`. This package only establishes the Marker model and initial assignments; it does not yet change crawler execution. The next integration step will make the pipeline apply these records before discovery.
