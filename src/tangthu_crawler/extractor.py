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

        selectors = (
            "article.fck_detail",
            "#article_content.fck_detail",
            "#article_content",
            "article.content_detail",
            ".content_detail.fck_detail",
            ".main_content_detail",
            ".fck_detail",
            "article",
            "main",
        )

        candidates = []
        seen_nodes = set()

        for selector in selectors:
            for candidate in soup.select(selector):
                marker = id(candidate)
                if marker in seen_nodes:
                    continue
                seen_nodes.add(marker)

                paragraph_count = len(candidate.select("p"))
                text = " ".join(candidate.stripped_strings)
                text_length = len(text)
                if paragraph_count < 2 and text_length < 300:
                    continue

                link_text = " ".join(
                    " ".join(node.stripped_strings)
                    for node in candidate.select("a")
                )
                link_ratio = len(link_text) / text_length if text_length else 1.0

                score = (
                    min(text_length, 12000) / 100
                    + min(paragraph_count, 40) * 2
                    - link_ratio * 20
                )
                candidates.append((score, candidate))

        if not candidates:
            raise ValueError("VnExpress article body container not found")

        _, container = max(candidates, key=lambda item: item[0])

        for node in container.select("script, style, noscript, nav, form"):
            node.decompose()

        blocks = []
        seen = set()
        for node in container.select("p, h2, h3, blockquote, figcaption"):
            value = " ".join(node.stripped_strings)
            if not value or value in seen:
                continue
            seen.add(value)
            blocks.append(value)

        body = "\n\n".join(blocks).strip()
        if not body:
            body = " ".join(container.stripped_strings).strip()

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
        image_node = container.select_one(
            "img[data-src], img[data-original], img[src]"
        )
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
