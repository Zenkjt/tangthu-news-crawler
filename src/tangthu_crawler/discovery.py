from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urlunparse
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

from .models import ArticleRef


class SourceDiscovery:
    """Discover article URLs using source-aware strategies.

    Vietnamese news sites commonly expose articles through category pages with
    numbered pagination. RSS is treated as optional, not as the primary source.
    """

    def __init__(self, source: dict, settings: dict):
        self.source = source
        crawler = settings.get("crawler", {})
        self.timeout = crawler.get("request_timeout", 20)
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": crawler.get("user_agent", "TangThuNewsCrawler/0.1")}
        )

    def discover(self) -> list[ArticleRef]:
        urls: list[str] = []
        methods = self.source.get("discovery", [])

        # Order matters: source-specific HTML/category discovery is primary for
        # Vietnamese news; sitemap is secondary and RSS is only a fallback.
        for method in methods:
            try:
                if method == "html":
                    urls.extend(self._html())
                elif method == "sitemap":
                    urls.extend(self._sitemap())
                elif method == "rss":
                    urls.extend(self._rss())
            except (requests.RequestException, ElementTree.ParseError) as exc:
                print(f"{self.source.get('id', 'source')}: {method} discovery failed: {exc}")

        return self._normalize(urls)

    def _get(self, url: str) -> str:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def _rss(self) -> list[str]:
        cfg = self.source.get("rss", {})
        feed_urls = list(cfg.get("feeds", []))
        index_url = cfg.get("index_url")

        if index_url:
            try:
                soup = BeautifulSoup(self._get(index_url), "html.parser")
                feed_urls.extend(
                    urljoin(index_url, a["href"])
                    for a in soup.find_all("a", href=True)
                    if a["href"].lower().endswith(".rss")
                )
            except requests.RequestException:
                pass

        urls: list[str] = []
        for feed_url in dict.fromkeys(feed_urls):
            try:
                root = ElementTree.fromstring(self._get(feed_url))
            except (requests.RequestException, ElementTree.ParseError):
                continue

            for element in root.iter():
                if element.tag.rsplit("}", 1)[-1] != "link":
                    continue
                href = element.attrib.get("href") or (element.text or "")
                if href.strip():
                    urls.append(urljoin(feed_url, href.strip()))
        return urls

    def _sitemap(self) -> list[str]:
        cfg = self.source.get("sitemap", {})
        paths = cfg.get("paths", ["/sitemap.xml"])
        urls: list[str] = []
        queue = [urljoin(self.source["url"], path) for path in paths]
        seen_maps: set[str] = set()

        while queue:
            sitemap_url = queue.pop(0)
            if sitemap_url in seen_maps:
                continue
            seen_maps.add(sitemap_url)

            try:
                root = ElementTree.fromstring(self._get(sitemap_url))
            except (requests.RequestException, ElementTree.ParseError):
                continue

            root_tag = root.tag.rsplit("}", 1)[-1]
            for element in root.iter():
                if element.tag.rsplit("}", 1)[-1] != "loc" or not element.text:
                    continue
                loc = urljoin(sitemap_url, element.text.strip())
                if root_tag == "sitemapindex":
                    queue.append(loc)
                else:
                    urls.append(loc)

        return urls

    def _html(self) -> list[str]:
        cfg = self.source.get("html", {})
        strategy = cfg.get("strategy", "links")

        if strategy == "category_pagination":
            return self._html_category_pagination(cfg)

        if strategy == "selector":
            return self._html_selector(cfg)

        return self._html_links(cfg)

    def _html_category_pagination(self, cfg: dict) -> list[str]:
        """Vietnamese-news pattern: /<category>-p1, /<category>-p2, ..."""
        categories = list(cfg.get("categories", []))
        pages = max(1, int(cfg.get("pages", 1)))
        template = cfg.get("page_url_template", "/{category}-p{page}")
        selector = cfg.get("article_link_selector", ".title-news a")
        max_urls = int(cfg.get("max_urls", 0))

        urls: list[str] = []
        for category in categories:
            for page in range(1, pages + 1):
                page_url = urljoin(
                    self.source["url"],
                    template.format(category=category, page=page),
                )
                try:
                    soup = BeautifulSoup(self._get(page_url), "html.parser")
                except requests.RequestException:
                    continue

                links = [
                    urljoin(page_url, anchor["href"])
                    for anchor in soup.select(selector)
                    if anchor.get("href")
                ]

                # Empty numbered pages mark the end of the useful range.
                if not links:
                    break

                urls.extend(links)
                if max_urls and len(urls) >= max_urls:
                    return urls[:max_urls]

        return urls

    def _html_selector(self, cfg: dict) -> list[str]:
        pages = cfg.get("pages", [self.source["url"]])
        selector = cfg.get("article_link_selector", "a[href]")
        urls: list[str] = []

        for page in pages:
            page_url = urljoin(self.source["url"], page)
            try:
                soup = BeautifulSoup(self._get(page_url), "html.parser")
            except requests.RequestException:
                continue
            urls.extend(
                urljoin(page_url, anchor["href"])
                for anchor in soup.select(selector)
                if anchor.get("href")
            )
        return urls

    def _html_links(self, cfg: dict) -> list[str]:
        pages = cfg.get("pages", [self.source["url"]])
        urls: list[str] = []

        for page in pages:
            page_url = urljoin(self.source["url"], page)
            try:
                soup = BeautifulSoup(self._get(page_url), "html.parser")
            except requests.RequestException:
                continue
            urls.extend(
                urljoin(page_url, anchor["href"])
                for anchor in soup.find_all("a", href=True)
            )
        return urls

    def _normalize(self, urls: list[str]) -> list[ArticleRef]:
        base_host = urlparse(self.source["url"]).netloc.lower()
        seen: set[str] = set()
        now = datetime.now(timezone.utc)
        result: list[ArticleRef] = []

        for raw in urls:
            url = self._canonicalize(raw)
            if not url or urlparse(url).netloc.lower() != base_host or url in seen:
                continue
            seen.add(url)
            result.append(ArticleRef(self.source["id"], url, now))
        return result

    @staticmethod
    def _canonicalize(url: str) -> str | None:
        try:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                return None
            return urlunparse(
                (parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", "")
            )
        except ValueError:
            return None
