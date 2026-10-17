from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urlunparse
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

from .models import ArticleRef


class SourceDiscovery:
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

        if "rss" in methods:
            urls.extend(self._rss())
        if "sitemap" in methods:
            urls.extend(self._sitemap())
        if "html" in methods and not urls:
            urls.extend(self._html())

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
        pages = cfg.get("pages", [self.source["url"]])
        urls: list[str] = []

        for page in pages:
            page_url = urljoin(self.source["url"], page)
            try:
                soup = BeautifulSoup(self._get(page_url), "html.parser")
            except requests.RequestException:
                continue
            urls.extend(
                urljoin(page_url, a["href"])
                for a in soup.find_all("a", href=True)
            )
        return urls

    def _normalize(self, urls: list[str]) -> list[ArticleRef]:
        base_host = urlparse(self.source["url"]).netloc
        seen: set[str] = set()
        now = datetime.now(timezone.utc)
        result: list[ArticleRef] = []

        for raw in urls:
            url = self._canonicalize(raw)
            if not url or urlparse(url).netloc != base_host or url in seen:
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
