from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from newspaper import Article


class ArticleExtractor:
    """Extract normalized articles, with source-specific adapters when needed."""

    def extract(self, html_path: str | Path, url: str, source: dict | None = None) -> dict:
        path = Path(html_path)
        html = path.read_text(encoding="utf-8", errors="replace")
        engine = (source or {}).get("extractor", {}).get("engine", "newspaper4k")

        if engine == "vnexpress":
            return self._extract_vnexpress(html, url)
        return self._extract_newspaper4k(html, url)

    def _extract_newspaper4k(self, html: str, url: str) -> dict:
        article = Article(url=url, fetch_images=False)
        article.download(input_html=html)
        article.parse()
        return {
            "url": url,
            "canonical_url": article.canonical_link or article.url,
            "title": article.title.strip(),
            "author": self._first_author(article.authors),
            "published_at": article.publish_date.isoformat() if article.publish_date else None,
            "body": article.text.strip(),
            "image": article.top_image or article.meta_img or None,
        }

    def _extract_vnexpress(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        container = None
        for selector in (
            "article.fck_detail",
            "#article_content.fck_detail",
            "#article_content",
            "article.content_detail",
            ".content_detail.fck_detail",
            ".main_content_detail",
        ):
            candidate = soup.select_one(selector)
            if candidate is None:
                continue
            paragraph_count = len(candidate.select("p"))
            text_length = len(candidate.get_text(" ", strip=True))
            if paragraph_count >= 1 or text_length >= 200:
                container = candidate
                break

        if container is None:
            raise ValueError("VnExpress article body container not found")

        for node in container.select("script, style, noscript"):
            node.decompose()

        blocks = []
        seen = set()
        for node in container.select("p, h2, h3, blockquote, figcaption"):
            text = " ".join(node.stripped_strings)
            if not text or text in seen:
                continue
            seen.add(text)
            blocks.append(text)

        body = "\n\n".join(blocks).strip()
        if not body:
            raise ValueError("VnExpress article body is empty")

        title_node = soup.select_one("h1.title-detail, h1")
        title = title_node.get_text(" ", strip=True) if title_node else ""

        description_node = soup.select_one("p.description, .description")
        description = (
            description_node.get_text(" ", strip=True)
            if description_node
            else ""
        )
        if description and description not in body:
            body = f"{description}\n\n{body}"

        date_node = soup.select_one("span.date, .date")
        published_at = self._parse_vnexpress_date(
            date_node.get_text(" ", strip=True) if date_node else ""
        )

        author = None
        for selector in (".author_mail", ".author", ".Normal strong"):
            node = soup.select_one(selector)
            if node:
                value = node.get_text(" ", strip=True)
                if value and len(value) <= 120:
                    author = value
                    break

        image = None
        image_node = container.select_one("img[data-src], img[data-original], img[src]")
        if image_node:
            image = (
                image_node.get("data-src")
                or image_node.get("data-original")
                or image_node.get("src")
            )
            if image:
                image = urljoin(url, image)

        canonical = soup.select_one('link[rel="canonical"]')
        canonical_url = canonical.get("href") if canonical else url
        canonical_url = urljoin(url, canonical_url)

        return {
            "url": url,
            "canonical_url": canonical_url,
            "title": title.strip(),
            "author": author,
            "published_at": published_at,
            "body": body,
            "image": image,
        }

    @staticmethod
    def _parse_vnexpress_date(value: str) -> str | None:
        if not value:
            return None
        for fmt in ("%d/%m/%Y, %H:%M (GMT+7)", "%d/%m/%Y, %H:%M"):
            try:
                return datetime.strptime(value, fmt).replace(
                    tzinfo=timezone(timedelta(hours=7))
                ).isoformat()
            except ValueError:
                pass
        return None

    @staticmethod
    def _first_author(authors: list[str]) -> str | None:
        for author in authors:
            value = author.strip()
            if value:
                return value
        return None
