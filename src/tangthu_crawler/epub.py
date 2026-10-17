from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ebooklib import epub


class EpubGenerator:
    """Build an EPUB edition from selected normalized Article Pool JSON files."""

    def __init__(self, timezone: str = "Asia/Ho_Chi_Minh"):
        self.timezone = ZoneInfo(timezone)

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

            articles.append(
                self._apply_policy(article, source.get("policy", {}))
            )

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

        for index, article in enumerate(articles, start=1):
            chapter = epub.EpubHtml(
                title=article.get("title") or f"Article {index}",
                file_name=f"article-{index}.xhtml",
                lang="vi",
            )
            chapter.content = self._article_html(article)
            book.add_item(chapter)
            chapters.append(chapter)

        book.toc = tuple(chapters)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav", *chapters]

        output.parent.mkdir(parents=True, exist_ok=True)
        epub.write_epub(str(output), book)
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

    @staticmethod
    def _article_html(article: dict) -> str:
        title = html.escape(article.get("title") or "Untitled")
        author = html.escape(article.get("author") or "")
        source = html.escape(article.get("source_id") or "")
        published = html.escape(article.get("published_at") or "")
        url = html.escape(
            article.get("canonical_url") or article.get("url") or ""
        )
        body = article.get("body") or ""

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
{paragraphs}
{link}
</body></html>"""
