import json
import zipfile
from pathlib import Path

from tangthu_crawler.epub import EpubGenerator


def _write_article(pool: Path, article_id: str, **extra) -> None:
    folder = pool / "fixture"
    folder.mkdir(parents=True, exist_ok=True)
    article = {
        "id": article_id,
        "source_id": "fixture",
        "url": f"https://example.com/{article_id}",
        "canonical_url": f"https://example.com/{article_id}",
        "title": "Test Article",
        "body": "First paragraph.\n\nSecond paragraph.",
    }
    article.update(extra)
    (folder / f"{article_id}.json").write_text(
        json.dumps(article),
        encoding="utf-8",
    )


def test_generate_without_image(tmp_path: Path):
    pool = tmp_path / "pool"
    _write_article(pool, "one")

    output = tmp_path / "0neNews.epub"
    EpubGenerator().generate(
        pool,
        output,
        sources=[{
            "id": "fixture",
            "status": "active",
            "policy": {"mode": "full_article"},
        }],
        article_ids={"one"},
    )

    with zipfile.ZipFile(output) as z:
        names = set(z.namelist())
        assert "EPUB/article-1.xhtml" in names
        assert not any(name.startswith("EPUB/images/") for name in names)


def test_image_is_embedded(monkeypatch, tmp_path: Path):
    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return b"\xff\xd8\xff\xd9"
        @property
        def headers(self):
            class Headers:
                def get_content_type(self):
                    return "image/jpeg"
            return Headers()

    monkeypatch.setattr(
        "tangthu_crawler.epub.urlopen",
        lambda request, timeout: FakeResponse(),
    )

    pool = tmp_path / "pool"
    _write_article(
        pool,
        "one",
        image="https://example.com/image.jpg",
    )

    output = tmp_path / "0neNews.epub"
    EpubGenerator().generate(
        pool,
        output,
        sources=[{
            "id": "fixture",
            "status": "active",
            "policy": {"mode": "full_article"},
        }],
        article_ids={"one"},
    )

    with zipfile.ZipFile(output) as z:
        names = set(z.namelist())
        image_names = [n for n in names if n.startswith("EPUB/images/")]
        assert len(image_names) == 1
        content = z.read("EPUB/article-1.xhtml").decode("utf-8")
        assert "images/" in content


def test_image_failure_does_not_break_edition(monkeypatch, tmp_path: Path):
    def fail(*args, **kwargs):
        raise OSError("image unavailable")

    monkeypatch.setattr("tangthu_crawler.epub.urlopen", fail)

    pool = tmp_path / "pool"
    _write_article(
        pool,
        "one",
        image="https://example.com/image.jpg",
    )

    output = tmp_path / "0neNews.epub"
    EpubGenerator().generate(
        pool,
        output,
        sources=[{
            "id": "fixture",
            "status": "active",
            "policy": {"mode": "full_article"},
        }],
        article_ids={"one"},
    )

    with zipfile.ZipFile(output) as z:
        assert "EPUB/article-1.xhtml" in z.namelist()
