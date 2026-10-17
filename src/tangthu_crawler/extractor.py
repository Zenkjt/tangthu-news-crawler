from __future__ import annotations

from pathlib import Path

from newspaper import Article


class ArticleExtractor:
    """Extract a normalized article from raw HTML using newspaper4k."""

    def extract(self, html_path: str | Path, url: str) -> dict:
        path = Path(html_path)

        article = Article(url=url)
        article.set_html(path.read_text(encoding="utf-8", errors="replace"))
        article.parse()

        return {
            "url": url,
            "canonical_url": article.url,
            "title": article.title.strip(),
            "author": self._first_author(article.authors),
            "published_at": article.publish_date.isoformat()
            if article.publish_date
            else None,
            "body": article.text.strip(),
            "image": article.top_image or None,
        }

    @staticmethod
    def _first_author(authors: list[str]) -> str | None:
        for author in authors:
            value = author.strip()
            if value:
                return value
        return None
