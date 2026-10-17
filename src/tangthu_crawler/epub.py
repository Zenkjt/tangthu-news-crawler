import shutil
from __future__ import annotations

import html
import json
import mimetypes
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from ebooklib import epub


class EpubGenerator:
    """Build a polished EPUB edition from normalized Article Pool JSON files."""

    def __init__(self, timezone: str = "Asia/Ho_Chi_Minh", image_timeout: int = 15):
        self.timezone = ZoneInfo(timezone)
        self.image_timeout = image_timeout

    def generate(
        self,
        article_pool: str | Path,
        output_path: str | Path,
        sources: list[dict],
        title: str = "YOUR NEWS",
        edition_time: str = "07:00",
        article_ids: set[str] | None = None,
    ) -> Path:
        pool = Path(article_pool)
        output = Path(output_path)
        source_map = {s["id"]: s for s in sources}

        articles: list[dict] = []
        for path in sorted(pool.glob("*/*.json")):
            if path.name.endswith(".meta.json"):
                continue

            article = json.loads(path.read_text(encoding="utf-8"))
            if article_ids is not None and article.get("id") not in article_ids:
                continue

            source = source_map.get(article.get("source_id"), {})
            if source.get("status", "active") != "active":
                continue

            article = self._apply_policy(article, source.get("policy", {}))
            articles.append(article)

        articles.sort(
            key=lambda a: a.get("published_at") or "",
            reverse=True,
        )

        now = datetime.now(self.timezone)
        date_label = now.strftime("%-d %B %Y")

        book = epub.EpubBook()
        book.set_identifier(f"tangthu-news-{now:%Y%m%d}")
        book.set_title(f"{title} at {edition_time} — {date_label}")
        book.set_language("vi")
        book.add_author("Tàng Thư")
        book.add_metadata("DC", "publisher", "Tàng Thư")
        book.add_metadata("DC", "description", f"{title} at {edition_time} — {date_label}")

        chapters = []

        intro = epub.EpubHtml(
            title="Edition",
            file_name="edition.xhtml",
            lang="vi",
        )
        intro.content = self._edition_html(
            title, edition_time, date_label, len(articles)
        )
        book.add_item(intro)
        chapters.append(intro)

        image_root = output.parent / ".epub-images"
        if image_root.exists():
            shutil.rmtree(image_root)
        image_root.mkdir(parents=True, exist_ok=True)

        for index, article in enumerate(articles, start=1):
            image_item = self._download_image(article, image_root, index)

            chapter = epub.EpubHtml(
                title=article.get("title") or f"Article {index}",
                file_name=f"article-{index}.xhtml",
                lang="vi",
            )
            chapter.content = self._article_html(article, image_item)
            book.add_item(chapter)
            chapters.append(chapter)

            if image_item is not None:
                book.add_item(image_item)

        book.toc = tuple(chapters)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav", *chapters]

        output.parent.mkdir(parents=True, exist_ok=True)
        epub.write_epub(str(output), book)

        shutil.rmtree(image_root, ignore_errors=True)
        return output

    @staticmethod
    def _apply_policy(article: dict, source_policy: dict) -> dict:
        mode = source_policy.get("mode", "excerpt")
        result = dict(article)
        body = result.get("body") or ""

        if mode == "metadata_only":
            result["body"] = ""
        elif mode == "excerpt":
            result["body"] = body[:800].strip()
        elif mode in {"full_article", "licensed"}:
            result["body"] = body
        else:
            result["body"] = body[:800].strip()

        return result

    @staticmethod
    def _edition_html(title, edition_time, date_label, article_count):
        return f"""<html><head><title>{html.escape(title)}</title></head>
<body>
<h1>{html.escape(title)} at {html.escape(edition_time)}</h1>
<p>{html.escape(date_label)}</p>
<p>{article_count} articles</p>
</body></html>"""

    def _download_image(
        self,
        article: dict,
        image_root: Path,
        index: int,
    ):
        image_url = article.get("image")
        if not image_url:
            return None

        try:
            request = Request(
                image_url,
                headers={"User-Agent": "TangThuNewsCrawler/0.1"},
            )
            with urlopen(request, timeout=self.image_timeout) as response:
                data = response.read()
                content_type = response.headers.get_content_type()

            extension = mimetypes.guess_extension(content_type) or Path(
                urlparse(image_url).path
            ).suffix.lower()

            if extension not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                extension = ".jpg"

            filename = f"article-{index}{extension}"
            path = image_root / filename
            path.write_bytes(data)

            media_type = (
                "image/jpeg" if extension in {".jpg", ".jpeg"}
                else f"image/{extension.lstrip('.')}"
            )

            item = epub.EpubItem(
                uid=f"image-{index}",
                file_name=f"images/{filename}",
                media_type=media_type,
                content=data,
            )
            return item
        except Exception:
            return None

    @staticmethod
    def _article_html(article: dict, image_item=None) -> str:
        title = html.escape(article.get("title") or "Untitled")
        author = html.escape(article.get("author") or "")
        source = html.escape(article.get("source_id") or "")
        published = html.escape(article.get("published_at") or "")
        url = html.escape(
            article.get("canonical_url") or article.get("url") or ""
        )
        body = article.get("body") or ""

        image = ""
        if image_item is not None:
            image = (
                f'<p><img src="{html.escape(image_item.file_name)}" '
                f'alt="{title}" /></p>'
            )

        paragraphs = "\n".join(
            f"<p>{html.escape(line.strip())}</p>"
            for line in body.splitlines()
            if line.strip()
        )

        meta = " · ".join(x for x in (source, published, author) if x)
        link = (
            f'<p><a href="{url}">Original article</a></p>'
            if url
            else ""
        )

        return f"""<html><head><title>{title}</title></head>
<body>
<h1>{title}</h1>
<p>{meta}</p>
{image}
{paragraphs}
{link}
</body></html>"""
