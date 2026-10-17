# PHASE 6 CHECKPOINT — EPUB GENERATION

## Status
Phase 6 implementation is complete. The CI failure was caused by the test fixture passing the source directory itself to `EpubGenerator.generate()`.

## Root cause
`EpubGenerator.generate()` is designed to receive the Article Pool root:

```text
data/article_pool/
├── vnexpress/
│   └── <article>.json
└── ...
```

Its scan is intentionally:

```python
pool.glob("*/*.json")
```

The test incorrectly passed:

```text
tmp_path/pool/fixture
```

so the generator searched:

```text
tmp_path/pool/fixture/*/*.json
```

and found no article. Therefore the generated EPUB correctly contained only the edition page, navigation, and OPF files.

## Correct fix
The tests now pass:

```text
tmp_path/pool/
└── fixture/
    └── abc.json
```

as the pool root.

No change to `src/tangthu_crawler/epub.py` is required.

## EPUB layout
The generator uses EbookLib and produces:

```text
mimetype
META-INF/container.xml
EPUB/content.opf
EPUB/edition.xhtml
EPUB/article-1.xhtml
EPUB/nav.xhtml
EPUB/toc.ncx
```

## Policy
- `metadata_only`: title/metadata + original link, no article body.
- `excerpt`: first 800 characters.
- `full_article`: full extracted body.
- `licensed`: full extracted body.
- unknown policy: excerpt fallback.

## Edition
Default:
- filename: `0neNews.epub`
- title: `YOUR NEWS at 07:00`
- timezone: `Asia/Ho_Chi_Minh`

## Not yet implemented
- Google Drive upload/overwrite
- per-user personalization
- OPDS integration
- production scheduling/distribution

These belong to later phases.
