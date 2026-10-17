from __future__ import annotations

from pathlib import Path

from newspaper import Article


class ArticleExtractor:
    """Extract a normalized article from stored raw HTML using newspaper4k."""

    def extract(self, html_path: str | Path, url: str) -> dict:
        path = Path(html_path)
        html = path.read_text(encoding="utf-8", errors="replace")

        article = Article(
            url=url,
            fetch_images=False,
        )

        # input_html belongs to download(), not Article.__init__().
        # This marks the Article as successfully downloaded without making
        # another HTTP request, then parse() operates on that cached HTML.
        article.download(input_html=html)
        article.parse()

        return {
            "url": url,
            "canonical_url": article.canonical_link or article.url,
            "title": article.title.strip(),
            "author": self._first_author(article.authors),
            "published_at": (
                article.publish_date.isoformat()
                if article.publish_date
                else None
            ),
            "body": article.text.strip(),
            "image": article.top_image or article.meta_img or None,
        }

    @staticmethod
    def _first_author(authors: list[str]) -> str | None:
        for author in authors:
            value = author.strip()
            if value:
                return value
        return None
