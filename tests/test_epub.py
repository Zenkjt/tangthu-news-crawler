import json
import zipfile
from pathlib import Path

from tangthu_crawler.epub import EpubGenerator


def test_generate_daily_epub(tmp_path: Path):
    pool = tmp_path / "pool" / "fixture"
    pool.mkdir(parents=True)

    article = {
        "id": "abc",
        "source_id": "fixture",
        "url": "https://example.com/article",
        "canonical_url": "https://example.com/article",
        "title": "Test Article",
        "author": "Test Author",
        "published_at": "2026-10-17T01:00:00+00:00",
        "body": "First paragraph.\n\nSecond paragraph.",
    }
    (pool / "abc.json").write_text(
        json.dumps(article, ensure_ascii=False),
        encoding="utf-8",
    )

    output = tmp_path / "0neNews.epub"
    EpubGenerator().generate(
        pool,
        output,
        sources=[{
            "id": "fixture",
            "name": "Fixture",
            "status": "active",
            "policy": {"mode": "full_article"},
        }],
    )

    assert output.exists()
    assert output.stat().st_size > 0

    with zipfile.ZipFile(output) as epub_file:
        names = set(epub_file.namelist())
        assert "mimetype" in names
        assert "OEBPS/article-1.xhtml" in names
        content = epub_file.read("OEBPS/article-1.xhtml").decode("utf-8")
        assert "Test Article" in content
        assert "First paragraph." in content
        assert "Original article" in content


def test_metadata_only_policy(tmp_path: Path):
    pool = tmp_path / "pool" / "fixture"
    pool.mkdir(parents=True)
    (pool / "abc.json").write_text(
        json.dumps({
            "id": "abc",
            "source_id": "fixture",
            "url": "https://example.com/article",
            "title": "Metadata Only",
            "body": "This must not be reproduced.",
        }),
        encoding="utf-8",
    )

    output = tmp_path / "0neNews.epub"
    EpubGenerator().generate(
        pool,
        output,
        sources=[{
            "id": "fixture",
            "status": "active",
            "policy": {"mode": "metadata_only"},
        }],
    )

    with zipfile.ZipFile(output) as epub_file:
        content = epub_file.read("OEBPS/article-1.xhtml").decode("utf-8")
        assert "This must not be reproduced." not in content
        assert "Metadata Only" in content
