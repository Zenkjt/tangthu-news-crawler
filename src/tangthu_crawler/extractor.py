from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from newspaper import Article
from trafilatura import bare_extraction


class ArticleExtractor:
    """Extract normalized articles using Trafilatura as the generic engine."""

    def extract(self, html_path: str | Path, url: str, source: dict | None = None) -> dict:
        path = Path(html_path)
        html = path.read_text(encoding="utf-8", errors="replace")
        engine = (source or {}).get("extractor", {}).get("engine", "trafilatura")

        if engine == "vnexpress":
            return self._extract_vnexpress(html, url)
        return self._extract_trafilatura(html, url)

    @staticmethod
    def _clean_text(value: str | None) -> str:
        """Normalize whitespace and decode HTML entities, including double-encoded ones."""
        if not value:
            return ""
        value = unescape(value)
        value = unescape(value)
        return " ".join(value.split())

    def _extract_trafilatura(self, html: str, url: str) -> dict:
        """Generic extraction: use Trafilatura's full fallback cascade with recall bias."""
        try:
            document = bare_extraction(
                html,
                url=url,
                favor_recall=True,
                include_comments=False,
                include_tables=True,
                include_images=False,
                include_links=False,
                with_metadata=True,
            )
        except Exception:
            document = None

        if document is not None:
            body = self._clean_paragraph_text(getattr(document, "text", None))
            title = self._clean_text(getattr(document, "title", None))
            author = self._clean_text(getattr(document, "author", None)) or None
            published_at = self._clean_text(getattr(document, "date", None)) or None
            extracted_url = self._clean_text(getattr(document, "url", None)) or url

            if body:
                result = {
                    "url": url,
                    "canonical_url": self._canonical_from_html(html, extracted_url),
                    "title": title,
                    "author": author,
                    "published_at": published_at,
                    "body": body,
                    "image": self._image_from_html(html, url),
                }

                if len(body) >= 300 and len(self._paragraphs(body)) >= 2:
                    return result

                fallback = self._extract_newspaper4k(html, url)
                if len(fallback.get("body", "")) > len(body):
                    return fallback
                return result

        return self._extract_newspaper4k(html, url)

    @staticmethod
    def _paragraphs(value: str) -> list[str]:
        return [part.strip() for part in value.splitlines() if part.strip()]

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

    def _extract_newspaper4k(self, html: str, url: str) -> dict:
        """Secondary rescue extractor for pages Trafilatura cannot usefully parse."""
        article = Article(url=url, fetch_images=False)
        try:
            article.download(input_html=html)
            article.parse()
        except Exception:
            return self._extract_legacy_dom(html, url)

        body = self._clean_paragraph_text(article.text)
        result = {
            "url": url,
            "canonical_url": article.canonical_link or article.url,
            "title": self._clean_text(article.title),
            "author": self._first_author(article.authors),
            "published_at": article.publish_date.isoformat() if article.publish_date else None,
            "body": body,
            "image": article.top_image or article.meta_img or self._image_from_html(html, url),
        }

        if len(body) < 300 or len(self._paragraphs(body)) < 2:
            fallback = self._extract_legacy_dom(html, url)
            if len(fallback.get("body", "")) > len(body):
                for key, value in fallback.items():
                    if value:
                        result[key] = value
        return result

    def _extract_legacy_dom(self, html: str, url: str) -> dict:
        """Last-resort compatibility extractor retained for unusual legacy pages."""
        soup = BeautifulSoup(html, "html.parser")
        for node in soup.select("script, style, noscript, nav, form, footer, header"):
            node.decompose()

        candidates = []
        selectors = (
            '[itemprop="articleBody"]', "article", "main", '[role="main"]',
            ".article-body", ".article__body", ".story-body", ".story__body",
            ".article-content", ".article__content", ".story-content",
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
        title_node = soup.select_one('meta[property="og:title"]') or soup.select_one("h1")
        title = (
            title_node.get("content") if title_node.name == "meta" else title_node.get_text(" ", strip=True)
        ) if title_node else ""
        canonical = self._canonical_from_html(html, url)
        published = None
        node = soup.select_one('meta[property="article:published_time"], meta[name="date"], time[datetime]')
        if node:
            published = node.get("content") or node.get("datetime")
        return {
            "url": url,
            "canonical_url": canonical,
            "title": self._clean_text(title),
            "author": None,
            "published_at": published,
            "body": body,
            "image": self._image_from_html(html, url),
        }

    @staticmethod
    def _canonical_from_html(html: str, fallback: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        node = soup.select_one('link[rel="canonical"]')
        if node and node.get("href"):
            return urljoin(fallback, node["href"])
        return fallback

    @staticmethod
    def _image_from_html(html: str, base_url: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        node = soup.select_one('meta[property="og:image"], meta[name="twitter:image"]')
        if node and node.get("content"):
            return urljoin(base_url, node["content"])
        return None

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
        image = image or self._image_from_html(html, url)

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
        cfg = (source or {}).get("quality_gate", {})
        if not cfg.get("enabled", False):
            return True, ""
        title = (article.get("title") or "").strip()
        body = (article.get("body") or "").strip()
        if cfg.get("require_title", True) and not title:
            return False, "missing_title"
        reject_titles = {str(x).strip().casefold() for x in cfg.get("reject_titles", [])}
        if title.casefold() in reject_titles:
            return False, "generic_title"
        min_chars = int(cfg.get("min_body_chars", 300))
        if len(body) < min_chars:
            return False, "body_too_short"
        min_paragraphs = int(cfg.get("min_paragraphs", 2))
        if len(ArticleExtractor._paragraphs(body)) < min_paragraphs:
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
            value = author.strip()
            if value:
                return value
        return None
