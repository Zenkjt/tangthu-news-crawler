from __future__ import annotations

import html
import json
import shutil
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ebooklib import epub


class EpubGenerator:
    def __init__(self, timezone="Asia/Ho_Chi_Minh", image_timeout=15):
        self.timezone = ZoneInfo(timezone)
        self.image_timeout = image_timeout

    def generate(
        self,
        article_pool,
        output_path,
        sources,
        title="YOUR NEWS",
        edition_time="07:00",
        article_ids: set[str] | None = None,
    ):
        pool = Path(article_pool)
        output = Path(output_path)
        source_map = {s["id"]: s for s in sources}
        allowed_ids = article_ids
        articles = []

        for path in sorted(pool.glob("*/*.json")):
            if path.name.endswith(".meta.json"):
                continue
            article = json.loads(path.read_text(encoding="utf-8"))
            if allowed_ids is not None and article.get("id") not in allowed_ids:
                continue
            source = source_map.get(article.get("source_id"), {})
            if source.get("status", "active") != "active":
                continue
            articles.append(
                self._apply_policy(article, source.get("policy", {}))
            )

        articles.sort(key=lambda a: a.get("published_at") or "", reverse=True)

        now = datetime.now(self.timezone)
        date_label = now.strftime("%-d %B %Y")

        book = epub.EpubBook()
        book.set_identifier(f"tangthu-news-{now:%Y%m%d}")
        book.set_title(f"{title} at {edition_time} — {date_label}")
        book.set_language("vi")
        book.add_author("Tàng Thư")
        book.add_metadata("DC", "publisher", "Tàng Thư")
        book.add_metadata(
            "DC",
            "description",
            f"{title} at {edition_time} — {date_label}",
        )

        edition = epub.EpubHtml(
            title="Edition",
            file_name="edition.xhtml",
            lang="vi",
        )
        edition.content = self._edition_html(
            title, edition_time, date_label, len(articles)
        )
        book.add_item(edition)

        article_chapters = []
        for index, article in enumerate(articles, start=1):
            chapter = epub.EpubHtml(
                title=article["title"] or f"Article {index}",
                file_name=f"article-{index}.xhtml",
                lang="vi",
            )
            chapter.content = self._article_html(article)
            book.add_item(chapter)
            article_chapters.append(chapter)

        toc_page = epub.EpubHtml(
            title="Mục lục",
            file_name="toc.xhtml",
            lang="vi",
        )
        toc_page.content = self._toc_html(articles, source_map)
        book.add_item(toc_page)

        source_groups = {}
        for chapter, article in zip(article_chapters, articles):
            source_id = article.get("source_id") or "Nguồn khác"
            source_groups.setdefault(source_id, []).append(chapter)

        book.toc = tuple(
            [
                epub.Link(
                    "toc.xhtml",
                    "Mục lục",
                    "toc-page",
                )
            ]
            + [
                epub.Section(
                    source_map.get(source_id, {}).get("name") or source_id,
                    tuple(chapters),
                )
                for source_id, chapters in source_groups.items()
            ]
        )

        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav", edition, toc_page, *article_chapters]

        image_root = output.parent / ".epub-images"
        if image_root.exists():
            shutil.rmtree(image_root, ignore_errors=True)

        output.parent.mkdir(parents=True, exist_ok=True)
        epub.write_epub(str(output), book)

        shutil.rmtree(image_root, ignore_errors=True)
        return output

    @staticmethod
    def _apply_policy(article, source_policy):
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
<h1>{html.escape(title)}</h1>
<p>{html.escape(edition_time)}</p>
<p>{html.escape(date_label)}</p>
<p>{article_count} articles</p>
</body></html>"""

    @staticmethod
    def _toc_html(articles, source_map):
        items = []
        current_source = None
        for index, article in enumerate(articles, start=1):
            source_id = article.get("source_id") or "Nguồn khác"
            source = source_map.get(source_id, {}).get("name") or source_id
            title = html.escape(article.get("title") or f"Article {index}")
            if source != current_source:
                if current_source is not None:
                    items.append("</ul>")
                items.append(
                    f"<li><strong>{html.escape(source)}</strong><ul>"
                )
                current_source = source
            items.append(
                f'<li><a href="article-{index}.xhtml">{title}</a></li>'
            )
        if current_source is not None:
            items.append("</ul></li>")
        return """<html><head><title>Mục lục</title></head>
<body>
<h1>Mục lục</h1>
<ul>
""" + "\n".join(items) + """
</ul>
</body></html>"""

    def _article_html(self, article):
        # Text nodes do not need quote/apostrophe escaping in XHTML.
        # Some e-readers display &quot; / &#x27; literally when those
        # entities are emitted by the generator.
        title = html.escape(
            article.get("title") or "Untitled",
            quote=False,
        )
        author = html.escape(
            article.get("author") or "",
            quote=False,
        )
        source = html.escape(
            article.get("source_id") or "",
            quote=False,
        )
        published = html.escape(
            article.get("published_at") or "",
            quote=False,
        )
        url = html.escape(
            article.get("canonical_url") or article.get("url") or ""
        )
        body = article.get("body") or ""

        paragraphs = "\n".join(
            f"<p>{html.escape(line.strip(), quote=False)}</p>"
            for line in body.splitlines()
            if line.strip()
        )
        if not paragraphs and body:
            paragraphs = f"<p>{html.escape(body, quote=False)}</p>"

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
