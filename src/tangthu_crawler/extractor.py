from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin
import json

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

    @staticmethod
    def _clean_text(value: str | None) -> str:
        """Normalize whitespace and decode HTML entities, including double-encoded ones."""
        if not value:
            return ""
        value = unescape(value)
        value = unescape(value)
        return " ".join(value.split())

    def _extract_newspaper4k(self, html: str, url: str) -> dict:
        article = Article(url=url, fetch_images=False)
        try:
            article.download(input_html=html)
            article.parse()
        except Exception:
            return self._extract_dom(html, url)

        body = self._clean_paragraph_text(article.text)
        result = {
            "url": url,
            "canonical_url": article.canonical_link or article.url,
            "title": self._clean_text(article.title),
            "author": self._first_author(article.authors),
            "published_at": article.publish_date.isoformat() if article.publish_date else None,
            "body": body,
            "image": article.top_image or article.meta_img or None,
        }

        # newspaper4k can parse the page but return an unusable body on
        # modern JS-heavy sites. Fall back to structured HTML extraction.
        if len(body) < 300 or len([p for p in body.splitlines() if p.strip()]) < 2:
            fallback = self._extract_dom(html, url)
            if len(fallback.get("body", "")) > len(body):
                for key, value in fallback.items():
                    if value:
                        result[key] = value
        return result

    @staticmethod
    def _clean_paragraph_text(value: str | None) -> str:
        if not value:
            return ""
        lines = []
        for raw in value.splitlines():
            line = ArticleExtractor._clean_text(raw)
            if line:
                lines.append(line)
        return "\n\n".join(lines)

    def _extract_dom(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        for node in soup.select("script, style, noscript, nav, form, footer, header"):
            node.decompose()

        # Prefer JSON-LD NewsArticle/articleBody when publishers expose it.
        jsonld = []
        for node in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(node.string or node.get_text())
            except Exception:
                continue
            values = data if isinstance(data, list) else [data]
            for value in values:
                if isinstance(value, dict) and isinstance(value.get("articleBody"), str):
                    jsonld.append(value)
        structured = max(jsonld, key=lambda x: len(x.get("articleBody", "")), default=None)

        candidates = []
        selectors = (
            '[itemprop="articleBody"]', 'article', 'main', '[role="main"]',
            '.article-body', '.article__body', '.story-body', '.story__body',
            '.article-content', '.article__content', '.story-content',
        )
        seen = set()
        for selector in selectors:
            for node in soup.select(selector):
                if id(node) in seen:
                    continue
                seen.add(id(node))
                paragraphs = [self._clean_text(p.get_text(" ", strip=True)) for p in node.select("p")]
                paragraphs = [p for p in paragraphs if p]
                text = "\n\n".join(dict.fromkeys(paragraphs))
                if len(text) >= 300:
                    link_text = self._clean_text(" ".join(a.get_text(" ", strip=True) for a in node.select("a")))
                    link_ratio = len(link_text) / len(text) if text else 1
                    score = min(len(text), 12000) / 100 + min(len(paragraphs), 40) * 2 - link_ratio * 20
                    candidates.append((score, text))

        body = max(candidates, key=lambda x: x[0])[1] if candidates else ""
        if structured and len(structured.get("articleBody", "")) > len(body):
            body = self._clean_paragraph_text(structured["articleBody"])

        title_value = (structured or {}).get("headline")
        if not title_value:
            node = soup.select_one('meta[property="og:title"]')
            title_value = node.get("content") if node else None
        if not title_value:
            node = soup.select_one("h1")
            title_value = node.get_text(" ", strip=True) if node else ""
        title = self._clean_text(title_value)

        published = (structured or {}).get("datePublished")
        if not published:
            node = soup.select_one('meta[property="article:published_time"], meta[name="date"], time[datetime]')
            published = (node.get("content") or node.get("datetime")) if node else None

        image = (structured or {}).get("image")
        if isinstance(image, dict):
            image = image.get("url")
        if isinstance(image, list):
            image = image[0] if image else None
        if not image:
            node = soup.select_one('meta[property="og:image"]')
            image = node.get("content") if node else None

        canonical = soup.select_one('link[rel="canonical"]')
        canonical_url = urljoin(url, canonical.get("href")) if canonical and canonical.get("href") else url
        return {
            "url": url,
            "canonical_url": canonical_url,
            "title": title,
            "author": (structured or {}).get("author") if isinstance((structured or {}).get("author"), str) else None,
            "published_at": published,
            "body": body,
            "image": urljoin(url, image) if image else None,
        }

    def _extract_vnexpress(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")

        selectors = (
            "article.fck_detail", "#article_content.fck_detail", "#article_content",
            "article.content_detail", ".content_detail.fck_detail", ".main_content_detail",
            ".fck_detail", "article", "main",
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
                text = self._clean_text(" ".join(candidate.stripped_strings))
                text_length = len(text)
                if paragraph_count < 2 and text_length < 300:
                    continue
                link_text = self._clean_text(" ".join(" ".join(node.stripped_strings) for node in candidate.select("a")))
                link_ratio = len(link_text) / text_length if text_length else 1.0
                score = min(text_length, 12000) / 100 + min(paragraph_count, 40) * 2 - link_ratio * 20
                candidates.append((score, candidate))

        if not candidates:
            raise ValueError("VnExpress article body container not found")
        _, container = max(candidates, key=lambda item: item[0])

        for node in container.select("script, style, noscript, nav, form"):
            node.decompose()

        blocks = []
        seen = set()
        for node in container.select("p, h2, h3, blockquote, figcaption"):
            value = self._clean_text(" ".join(node.stripped_strings))
            if not value or value in seen:
                continue
            seen.add(value)
            blocks.append(value)
        body = "\n\n".join(blocks).strip()
        if not body:
            body = self._clean_text(" ".join(container.stripped_strings))
        if not body:
            raise ValueError("VnExpress article body is empty")

        title_node = soup.select_one("h1.title-detail, h1")
        title = self._clean_text(title_node.get_text(" ", strip=True)) if title_node else ""

        description_node = soup.select_one("p.description, .description")
        description = self._clean_text(description_node.get_text(" ", strip=True)) if description_node else ""
        if description and description not in body:
            body = f"{description}\n\n{body}"

        date_node = soup.select_one("span.date, .date")
        published_at = self._parse_vnexpress_date(date_node.get_text(" ", strip=True) if date_node else "")

        author = None
        for selector in (".author_mail", ".author", ".Normal strong"):
            node = soup.select_one(selector)
            if node:
                value = self._clean_text(node.get_text(" ", strip=True))
                if value and len(value) <= 120:
                    author = value
                    break

        image = None
        image_node = container.select_one("img[data-src], img[data-original], img[src]")
        if image_node:
            image = image_node.get("data-src") or image_node.get("data-original") or image_node.get("src")
            if image:
                image = urljoin(url, image)

        canonical = soup.select_one('link[rel="canonical"]')
        canonical_url = canonical.get("href") if canonical else url
        canonical_url = urljoin(url, canonical_url)

        return {
            "url": url, "canonical_url": canonical_url, "title": title.strip(),
            "author": author, "published_at": published_at, "body": body, "image": image,
        }

    @staticmethod
    def quality_check(article: dict, source: dict | None = None) -> tuple[bool, str]:
        """Reject listing/tag-like pages after fetch, using source-configurable thresholds."""
        cfg=(source or {}).get("quality_gate", {})
        if not cfg.get("enabled", False):
            return True, ""
        title=(article.get("title") or "").strip()
        body=(article.get("body") or "").strip()
        if cfg.get("require_title", True) and not title:
            return False, "missing_title"
        reject_titles={str(x).strip().casefold() for x in cfg.get("reject_titles", [])}
        if title.casefold() in reject_titles:
            return False, "generic_title"
        min_chars=int(cfg.get("min_body_chars", 300))
        if len(body) < min_chars:
            return False, "body_too_short"
        min_paragraphs=int(cfg.get("min_paragraphs", 2))
        paragraphs=[p for p in body.splitlines() if p.strip()]
        if len(paragraphs) < min_paragraphs:
            return False, "too_few_paragraphs"
        return True, ""

    @staticmethod
    def _parse_vnexpress_date(value: str) -> str | None:
        if not value:
            return None
        for fmt in ("%d/%m/%Y, %H:%M (GMT+7)", "%d/%m/%Y, %H:%M"):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=timezone(timedelta(hours=7))).isoformat()
            except ValueError:
                pass
        return None

    @staticmethod
    def _first_author(authors: list[str]) -> str | None:
        for author in authors:
            value=author.strip()
            if value:
                return value
        return None
