from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from .models import ArticleRef


class VnExpressTopicAdapter:
    """Discovery adapter for VnExpress homepage and topic/category listings.

    Each registered source URL is its own discovery profile. When a profile
    defines article containers, extraction is strictly scoped to those
    containers and preserves their document order.
    """

    ARTICLE_PATH_RE = re.compile(r"-[0-9]+\.html$", re.I)
    PAGE_SUFFIX_RE = re.compile(
        r"(?P<base>.*?)(?:-p(?P<page>\d+)|/p(?P<slash_page>\d+)|/page/(?P<page_dir>\d+))$",
        re.I,
    )
    EXCLUDED_PREFIXES = (
        "/tac-gia/", "/author/", "/chu-de/", "/tag/", "/video/",
        "/photo/", "/podcast/", "/live/", "/tim-kiem/", "/search/",
    )
    DEFAULT_ARTICLE_SELECTORS = (
        "h3.title-news a",
        "h2.title-news a",
    )
    DEFAULT_NEXT_SELECTORS = (
        'a[rel~="next"]',
        ".pagination a.next",
        "a.btn-next",
    )

    def __init__(self, source: dict, session: requests.Session, timeout: int = 20):
        self.source = source
        self.session = session
        self.timeout = timeout
        self.cfg = source.get("html", {})
        self.max_articles = max(1, int(self.cfg.get("max_articles", 20)))
        self.max_pages = max(1, int(self.cfg.get("max_pages", 4)))
        self.container_selectors = tuple(
            self.cfg.get("article_container_selectors") or ()
        )
        self.article_selectors = tuple(
            self.cfg.get("article_link_selectors") or self.DEFAULT_ARTICLE_SELECTORS
        )
        self.next_selectors = tuple(
            self.cfg.get("next_page_selectors") or self.DEFAULT_NEXT_SELECTORS
        )

    def discover(self) -> list[ArticleRef]:
        start_url = self._canonicalize(self.source["url"])
        if not start_url:
            return []

        urls: list[str] = []
        seen_articles: set[str] = set()
        seen_pages: set[str] = set()
        page_url = start_url

        for page_index in range(self.max_pages):
            page_url = self._canonicalize(page_url)
            if not page_url or page_url in seen_pages:
                break
            seen_pages.add(page_url)

            try:
                response = self.session.get(
                    page_url,
                    timeout=self.timeout,
                    allow_redirects=True,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                print(
                    f"{self.source.get('id', 'vnexpress')}: "
                    f"topic page failed {page_url}: {type(exc).__name__}: {exc}"
                )
                break

            final_url = self._canonicalize(response.url or page_url) or page_url
            soup = BeautifulSoup(response.text, "html.parser")
            page_urls = self._extract_article_links(soup, final_url)

            added = 0
            for article_url in page_urls:
                canonical = self._canonicalize(article_url)
                if not canonical or canonical in seen_articles:
                    continue
                seen_articles.add(canonical)
                urls.append(canonical)
                added += 1
                if len(urls) >= self.max_articles:
                    break

            print(
                f"{self.source.get('id', 'vnexpress')}: "
                f"topic_page={page_index + 1} url={final_url} "
                f"new_articles={added} total={len(urls)}"
            )

            if len(urls) >= self.max_articles:
                break

            next_url = self._find_next_page(soup, final_url, start_url)
            if not next_url or next_url in seen_pages:
                break
            page_url = next_url

        discovered_at = datetime.now(timezone.utc)
        return [
            ArticleRef(self.source["id"], url, discovered_at)
            for url in urls[: self.max_articles]
        ]

    def _extract_article_links(self, soup: BeautifulSoup, page_url: str) -> list[str]:
        # A configured container is authoritative. Never fall back to the
        # whole page: VnExpress pages contain separate "Đọc nhiều" highlights
        # before the actual article stream.
        containers = []
        if self.container_selectors:
            for selector in self.container_selectors:
                containers.extend(soup.select(selector))
            if not containers:
                print(
                    f"{self.source.get('id', 'vnexpress')}: "
                    f"article container not found; selectors={self.container_selectors}"
                )
                return []
        else:
            containers = [soup]

        links: list[str] = []
        seen: set[str] = set()
        for container in containers:
            for selector in self.article_selectors:
                for anchor in container.select(selector):
                    href = anchor.get("href")
                    if not href:
                        continue
                    candidate = self._canonicalize(urljoin(page_url, href))
                    if not candidate or not self._is_article_url(candidate):
                        continue
                    if candidate not in seen:
                        seen.add(candidate)
                        links.append(candidate)

        # Strict fallback is allowed only when no container was configured.
        # This avoids reintroducing popular/highlight links into a feed.
        if not links and not self.container_selectors:
            for anchor in soup.find_all("a", href=True):
                candidate = self._canonicalize(urljoin(page_url, anchor["href"]))
                if not candidate or not self._is_article_url(candidate):
                    continue
                if candidate not in seen:
                    seen.add(candidate)
                    links.append(candidate)

        return links

    def _is_article_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if not self._same_site(parsed.hostname):
            return False
        path = parsed.path.lower()
        if any(path.startswith(prefix) for prefix in self.EXCLUDED_PREFIXES):
            return False
        configured = self.cfg.get("excluded_path_prefixes", [])
        if any(path.startswith(str(prefix).lower()) for prefix in configured):
            return False
        return bool(self.ARTICLE_PATH_RE.search(path))

    def _find_next_page(
        self,
        soup: BeautifulSoup,
        current_url: str,
        profile_url: str,
    ) -> str | None:
        current_number = self._page_number(current_url)
        if current_number is None:
            current_number = 1
        profile_base = self._page_base(profile_url)

        candidates: list[tuple[int, int, str]] = []
        explicit_nodes = []
        for selector in self.next_selectors:
            explicit_nodes.extend(soup.select(selector))

        explicit_ids = {id(node) for node in explicit_nodes}
        for position, anchor in enumerate(soup.find_all("a", href=True)):
            candidate = self._canonicalize(urljoin(current_url, anchor["href"]))
            if not candidate or not self._same_site(urlparse(candidate).hostname):
                continue
            if self._page_base(candidate) != profile_base:
                continue

            page_number = self._page_number(candidate)
            if page_number is None or page_number <= current_number:
                continue

            rel = anchor.get("rel", [])
            if isinstance(rel, str):
                rel = rel.split()
            text = " ".join(anchor.stripped_strings).strip().casefold()
            classes = {str(value).casefold() for value in anchor.get("class", [])}
            is_explicit = id(anchor) in explicit_ids or "next" in rel or "next" in classes
            is_next_text = text in {
                "tiếp", "trang tiếp", "sau", "next", "next page", "›", "»", "→", ">"
            }
            if not is_explicit and not is_next_text:
                continue

            score = 1 if is_explicit or is_next_text else 0
            candidates.append((page_number, -score, candidate))

        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        return candidates[0][2]

    @classmethod
    def _page_number(cls, url: str) -> int | None:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        for key in ("page", "p"):
            if query.get(key) and query[key][0].isdigit():
                return int(query[key][0])

        match = cls.PAGE_SUFFIX_RE.search(parsed.path.rstrip("/"))
        if not match:
            return None
        value = match.group("page") or match.group("slash_page") or match.group("page_dir")
        return int(value) if value else None

    @classmethod
    def _page_base(cls, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        match = cls.PAGE_SUFFIX_RE.search(path)
        if match:
            path = match.group("base")
        return f"{parsed.scheme.lower()}://{(parsed.hostname or '').lower()}{path}"

    def _same_site(self, hostname: str | None) -> bool:
        source_host = (urlparse(self.source["url"]).hostname or "").lower()
        host = (hostname or "").lower()
        if not source_host or not host:
            return False
        return (
            host == source_host
            or host.endswith("." + source_host)
            or source_host.endswith("." + host)
        )

    @staticmethod
    def _canonicalize(url: str) -> str | None:
        try:
            parsed = urlparse(str(url).strip())
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                return None
            host = parsed.hostname.lower()
            if host == "www.vnexpress.net":
                host = "vnexpress.net"
            netloc = host
            if parsed.port:
                netloc = f"{host}:{parsed.port}"
            page_query = []
            for key in ("page", "p"):
                for value in parse_qs(parsed.query).get(key, []):
                    if value.isdigit():
                        page_query.append((key, value))
            query = urlencode(page_query)
            return urlunparse(
                ("https", netloc, parsed.path.rstrip("/"), "", query, "")
            )
        except (TypeError, ValueError):
            return None
