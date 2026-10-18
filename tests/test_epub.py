import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from tangthu_crawler.epub import EpubGenerator
from tangthu_crawler.validator import EpubValidationError, validate_epub


def _write_article(pool: Path, article_id: str, source_id="fixture", **extra) -> None:
    folder = pool / source_id
    folder.mkdir(parents=True, exist_ok=True)
    article = {
        "id": article_id,
        "source_id": source_id,
        "url": f"https://example.com/{article_id}",
        "canonical_url": f"https://example.com/{article_id}",
        "title": f"Test Article {article_id}",
        "body": "First paragraph.\n\nSecond paragraph.",
    }
    article.update(extra)
    (folder / f"{article_id}.json").write_text(
        json.dumps(article),
        encoding="utf-8",
    )


def _navmap(root):
    ns = {"ncx": "http://www.daisy.org/z3986/2005/ncx/"}
    return root.find("ncx:navMap", ns), ns


def test_generated_epub_passes_structural_validation(tmp_path: Path):
    pool = tmp_path / "pool"
    _write_article(pool, "one")

    output = tmp_path / "0neNews.epub"
    EpubGenerator().generate(
        pool,
        output,
        sources=[{
            "id": "fixture",
            "name": "Fixture News",
            "status": "active",
            "policy": {"mode": "full_article"},
        }],
        article_ids={"one"},
    )

    validate_epub(output)

    with zipfile.ZipFile(output) as z:
        toc = z.read("EPUB/toc.xhtml").decode("utf-8")
        nav = z.read("EPUB/nav.xhtml").decode("utf-8")
        assert "Mục lục" in toc
        assert "Fixture News" in toc
        assert "Test Article one" in toc
        assert "article-1.xhtml" in toc
        assert "Fixture News" in nav
        assert "article-1.xhtml" in nav
        assert "toc.xhtml" not in nav


def test_validator_rejects_broken_epub(tmp_path: Path):
    output = tmp_path / "broken.epub"
    with zipfile.ZipFile(output, "w") as z:
        z.writestr("mimetype", "wrong")

    with pytest.raises(EpubValidationError):
        validate_epub(output)


def test_toc_has_one_hierarchy_level_per_source(tmp_path: Path):
    pool = tmp_path / "pool"
    _write_article(pool, "one", source_id="source_a")
    _write_article(pool, "two", source_id="source_a")
    _write_article(pool, "three", source_id="source_b")

    output = tmp_path / "0neNews.epub"
    EpubGenerator().generate(
        pool,
        output,
        sources=[
            {"id": "source_a", "name": "Nguồn A", "status": "active", "policy": {"mode": "full_article"}},
            {"id": "source_b", "name": "Nguồn B", "status": "active", "policy": {"mode": "full_article"}},
        ],
        article_ids={"one", "two", "three"},
    )

    with zipfile.ZipFile(output) as z:
        toc = z.read("EPUB/toc.xhtml").decode("utf-8")
        assert toc.count("<strong>Nguồn A</strong>") == 1
        assert toc.count("<strong>Nguồn B</strong>") == 1
        assert "Test Article one" in toc
        assert "Test Article two" in toc
        assert "Test Article three" in toc


def test_native_toc_uses_crosspoint_hierarchy(tmp_path: Path):
    pool = tmp_path / "pool"
    _write_article(pool, "one", source_id="source_a")
    _write_article(pool, "two", source_id="source_a")
    _write_article(pool, "three", source_id="source_b")

    output = tmp_path / "0neNews.epub"
    EpubGenerator().generate(
        pool,
        output,
        sources=[
            {"id": "source_a", "name": "Nguồn A", "status": "active", "policy": {"mode": "full_article"}},
            {"id": "source_b", "name": "Nguồn B", "status": "active", "policy": {"mode": "full_article"}},
        ],
        article_ids=["one", "two", "three"],
    )

    with zipfile.ZipFile(output) as z:
        ncx = ET.fromstring(z.read("EPUB/toc.ncx"))

    nav_map, ns = _navmap(ncx)
    assert nav_map is not None

    top_level = nav_map.findall("ncx:navPoint", ns)
    assert len(top_level) == 2

    assert [
        p.find("ncx:navLabel/ncx:text", ns).text for p in top_level
    ] == ["Nguồn A", "Nguồn B"]

    assert [
        p.find("ncx:content", ns).attrib["src"] for p in top_level
    ] == ["article-1.xhtml", "article-3.xhtml"]

    first_children = top_level[0].findall("ncx:navPoint", ns)
    second_children = top_level[1].findall("ncx:navPoint", ns)

    assert [
        p.find("ncx:navLabel/ncx:text", ns).text for p in first_children
    ] == ["Test Article one", "Test Article two"]
    assert [
        p.find("ncx:navLabel/ncx:text", ns).text for p in second_children
    ] == ["Test Article three"]

    assert [
        p.find("ncx:content", ns).attrib["src"] for p in first_children
    ] == ["article-1.xhtml", "article-2.xhtml"]
    assert [
        p.find("ncx:content", ns).attrib["src"] for p in second_children
    ] == ["article-3.xhtml"]

    # Source rows are parents; article rows are children. CrossPoint uses
    # this NCX depth to indent level-2 entries in Select Chapter.
    assert all(
        p.find("ncx:navPoint", ns) is not None
        for p in top_level
    )
    assert all(
        p.find("ncx:content", ns).attrib["src"] != "toc.xhtml"
        for p in top_level
    )
