# Checkpoint — VnExpress Hà Nội Today article selector
Date: 2026-11-18
Repository: `Zenkjt/tangthu-news-crawler`
Branch: `vnexpress-topic-adapter`

## Evidence
GitHub Actions live diagnostic for `https://vnexpress.net/thoi-su/ha-noi-today`:
- HTTP 200; expected final URL and page title.
- Main listing container: `.list-article`.
- Four article cards have `article.article-item`.
- Article title links are `h2.title-news a`.
- Existing selector `article.item-news h2.title-news a` does not match those cards.
- Secondary `.list-news-subfolder` blocks are intentionally excluded.

## Decision
Keep the existing `article.item-news` selector for other VnExpress templates such as Góc nhìn.
Add the narrow selector `article.article-item h2.title-news a` for the current Hà Nội Today template.
Do not broaden to `.list-article a[href]`: that would include thumbnail and comment links as well as title links.

## Files
- `config/sources/vnexpress.yaml`: add the article-item title selector.
- `tests/test_vnexpress_adapter.py`: change the Hà Nội fixture to match the observed live DOM (`article.article-item > h2.title-news > a`).
- No change to adapter implementation or smoke-test script.
- Pagination remains out of scope for this one-page smoke test.

## Validation
The live DOM evidence comes from the supplied GitHub Actions log. The updated test fixture mirrors that structure.
Run the adapter tests and then the Hà Nội live smoke test in GitHub Actions. This package has not been executed against the repository's full test suite or a live endpoint here.
