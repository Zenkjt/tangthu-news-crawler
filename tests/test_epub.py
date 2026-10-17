import json
import zipfile
from pathlib import Path

from tangthu_crawler.epub import EpubGenerator


ARTICLE_PATH = "EPUB/article-1.xhtml"


def _write_article(pool: Path, article_id: str, title: str) -> None:
    folder = pool / "fixture"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{article_id}.json").write_text(
        json.dumps({
            "id": article_id,
            "source_id": "fixture",
            "url": f"https://example.com/{article_id}",
            "canonical_url": f"https://example.com/{article_id}",
            "title": title,
            "body": f"Body for {title}.",
        }),
        encoding="utf-8",
    )


def test_generator_can_limit_edition_to_current_run(tmp_path: Path):
    pool = tmp_path / "pool"
    _write_article(pool, "old", "Old Article")
    _write_article(pool, "new", "New Article")

    output = tmp_path / "0neNews.epub"
    EpubGenerator().generate(
        pool,
        output,
        sources=[{
            "id": "fixture",
            "status": "active",
            "policy": {"mode": "full_article"},
        }],
        article_ids={"new"},
    )

    with zipfile.ZipFile(output) as epub_file:
        names = set(epub_file.namelist())
        assert "EPUB/article-1.xhtml" in names
        assert "EPUB/article-2.xhtml" not in names
        content = epub_file.read("EPUB/article-1.xhtml").decode("utf-8")
        assert "New Article" in content
        assert "Old Article" not in content


def test_empty_current_run_produces_valid_edition(tmp_path: Path):
    pool = tmp_path / "pool"
    _write_article(pool, "old", "Old Article")

    output = tmp_path / "0neNews.epub"
    EpubGenerator().generate(
        pool,
        output,
        sources=[{
            "id": "fixture",
            "status": "active",
            "policy": {"mode": "full_article"},
        }],
        article_ids=set(),
    )

    with zipfile.ZipFile(output) as epub_file:
        names = set(epub_file.namelist())
        assert "mimetype" in names
        assert "EPUB/edition.xhtml" in names
        assert "EPUB/article-1.xhtml" not in names
