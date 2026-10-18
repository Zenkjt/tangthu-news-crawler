from __future__ import annotations
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urlunparse
from xml.etree import ElementTree
import requests
from bs4 import BeautifulSoup
from .models import ArticleRef


class SourceDiscovery:
    """Bounded HTML discovery with generic article-link scoring."""

    ARTICLE_HREF_RE = re.compile(r"/[^/?#]+-\d+\.html(?:$|[?#])", re.I)
    DATE_RE = re.compile(r"/(?:19|20)\d{2}/\d{1,2}/\d{1,2}(?:/|$)")
    ARTICLE_HINTS = ("/article/", "/articles/", "/story/", "/news/", "/world/", "/politics/", "/business/", "/technology/", "/science/", "/health/", "/culture/", "/sport/", "/vietnamese/")
    EXCLUDED_PREFIXES = ("/video/", "/videos/", "/live/", "/audio/", "/podcast/", "/search", "/author/", "/authors/", "/tag/", "/tags/", "/category/", "/topics/", "/topic/", "/newsletter/", "/about/", "/contact/", "/privacy/", "/terms/")

    def __init__(self, source: dict, settings: dict):
        self.source = source
        crawler = settings.get("crawler", {})
        self.timeout = crawler.get("request_timeout", 20)
        self.session = requests.Session()
        user_agent = crawler.get(
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36",
        )
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "vi,en-US;q=0.8,en;q=0.6",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        self.session.headers.update(source.get("http", {}).get("headers", {}))

    def discover(self) -> list[ArticleRef]:
        urls = []
        for method in self.source.get("discovery", []):
            try:
                if method == "html":
                    urls.extend(self._html())
                elif method == "sitemap":
                    urls.extend(self._sitemap())
                elif method == "rss":
                    urls.extend(self._rss())
            except (requests.RequestException, ElementTree.ParseError) as exc:
                print(f"{self.source.get('id','source')}: {method} discovery failed: {exc}")
        return self._normalize(urls)

    def _get(self, url):
        r = self.session.get(url, timeout=self.timeout, allow_redirects=True)
        print(
            f"{self.source.get('id','source')}: HTTP status={r.status_code} "
            f"final_url={r.url} content_type={r.headers.get('Content-Type','')} "
            f"bytes={len(r.content)} server={r.headers.get('Server','-')}"
        )
        print(f"{self.source.get('id','source')}: user_agent={self.session.headers.get('User-Agent')}")
        r.raise_for_status()
        return r.text

    def _html(self):
        cfg = self.source.get("html", {})
        strategy = cfg.get("strategy", "generic")
        if strategy == "page_articles":
            return self._html_page_articles(cfg)
        if strategy == "category_pagination":
            return self._html_category_pagination(cfg)
        if strategy == "selector":
            return self._html_selector(cfg)
        return self._html_generic(cfg)

    def _html_page_articles(self, cfg):
        page_url = self.source["url"]
        limit = max(1, int(cfg.get("max_articles", 20)))
        selectors = cfg.get("article_link_selectors", [".title-news a", "article h3 a", "article h2 a"])
        try:
            soup = BeautifulSoup(self._get(page_url), "html.parser")
        except requests.RequestException as exc:
            print(f"{self.source.get('id','source')}: page fetch failed {page_url}: {exc}")
            return []

        links, seen = [], set()
        for selector in selectors:
            for a in soup.select(selector):
                href = a.get("href")
                if not href:
                    continue
                url = self._canonicalize(urljoin(page_url, href))
                if not url or url in seen or not self._is_article_url(url):
                    continue
                seen.add(url)
                links.append(url)
                if len(links) >= limit:
                    print(f"{self.source.get('id','source')}: page={page_url} article_links={len(links)} max={limit}")
                    return links

        print(f"{self.source.get('id','source')}: page={page_url} article_links={len(links)} max={limit}")
        return links

    def _html_generic(self, cfg):
        page_url = self.source["url"]
        limit = max(1, int(cfg.get("max_articles", 20)))
        try:
            soup = BeautifulSoup(self._get(page_url), "html.parser")
        except requests.RequestException as exc:
            print(f"{self.source.get('id','source')}: page fetch failed {page_url}: {exc}")
            return []
        return self._generic_links(soup, page_url, limit, set())

    def _generic_links(self, soup, page_url, limit, seen):
        candidates = []
        source_host = urlparse(self.source["url"]).netloc.lower()
        excluded = tuple(self.source.get("html", {}).get("excluded_path_prefixes", [])) + self.EXCLUDED_PREFIXES
        for position, a in enumerate(soup.find_all("a", href=True)):
            url = self._canonicalize(urljoin(page_url, a["href"]))
            if not url or url in seen:
                continue
            parsed = urlparse(url)
            if parsed.netloc.lower() != source_host:
                continue
            score = self._score_link(a, parsed.path, excluded)
            if score < int(self.source.get("html", {}).get("min_link_score", 4)):
                continue
            candidates.append((score, -position, url))
            seen.add(url)

        candidates.sort(reverse=True)
        links = [url for _, _, url in candidates[:limit]]
        print(f"{self.source.get('id','source')}: page={page_url} article_links={len(links)} max={limit}")
        return links

    def _score_link(self, anchor, path, excluded):
        p = path.lower()
        if not p or p == "/":
            return -100
        excluded_prefixes = tuple(x.lower().rstrip("/") + "/" for x in excluded)
        if any(p.startswith(prefix) or (prefix != "/" and prefix.rstrip("/") in p) for prefix in excluded_prefixes):
            return -100

        score = 0
        text = " ".join(anchor.stripped_strings)
        if len(text) >= 30:
            score += 2
        elif len(text) >= 12:
            score += 1
        if self.DATE_RE.search(p):
            score += 4
        if self.ARTICLE_HREF_RE.search(p):
            score += 4
        if any(hint in p for hint in self.ARTICLE_HINTS):
            score += 2
        if p.endswith(".html"):
            score += 2
        if p.count("/") >= 3:
            score += 1
        if len(p.rsplit("/", 1)[-1]) >= 18:
            score += 1
        if anchor.find_parent("article"):
            score += 3
        if anchor.find_parent(["h1", "h2", "h3", "h4"]):
            score += 2
        if anchor.find("img"):
            score += 1
        if any(token in p for token in ("/login", "/subscribe", "/account", "/sitemap", "/rss")):
            score -= 10
        return score

    def _is_article_url(self, url):
        path = urlparse(url).path.lower()
        configured_prefixes = self.source.get("html", {}).get("excluded_path_prefixes", [])
        if self.source.get("id") == "vnexpress":
            configured_prefixes = [
                "/tac-gia/", "/author/", "/chu-de/", "/video/", *configured_prefixes,
            ]
        article_pattern = self.source.get("html", {}).get("article_href_regex")
        if article_pattern:
            return bool(re.search(article_pattern, path))
        excluded_prefixes = tuple(p.lower().rstrip("/") + "/" for p in configured_prefixes)
        if any(path.startswith(prefix) for prefix in excluded_prefixes):
            return False
        return bool(self.ARTICLE_HREF_RE.search(path))

    def _html_category_pagination(self, cfg):
        urls = []
        pages = max(1, int(cfg.get("pages", 1)))
        template = cfg.get("page_url_template", "/{category}-p{page}")
        selector = cfg.get("article_link_selector", ".title-news a")
        for category in cfg.get("categories", []):
            for page in range(1, pages + 1):
                page_url = urljoin(self.source["url"], template.format(category=category, page=page))
                try:
                    soup = BeautifulSoup(self._get(page_url), "html.parser")
                except requests.RequestException as exc:
                    print(f"{self.source.get('id','source')}: page fetch failed {page_url}: {exc}")
                    continue
                links = [urljoin(page_url, a["href"]) for a in soup.select(selector) if a.get("href")]
                if not links:
                    break
                urls.extend(links)
                if cfg.get("max_urls") and len(urls) >= int(cfg["max_urls"]):
                    return urls[:int(cfg["max_urls"])]
        return urls

    def _html_selector(self, cfg):
        urls = []
        for page in cfg.get("pages", [self.source["url"]]):
            page_url = urljoin(self.source["url"], page)
            try:
                soup = BeautifulSoup(self._get(page_url), "html.parser")
            except requests.RequestException as exc:
                print(f"{self.source.get('id','source')}: page fetch failed {page_url}: {exc}")
                continue
            urls.extend(urljoin(page_url, a["href"]) for a in soup.select(cfg.get("article_link_selector", "a[href]")) if a.get("href"))
        return urls

    def _rss(self):
        cfg = self.source.get("rss", {})
        feeds = list(cfg.get("feeds", []))
        if cfg.get("index_url"):
            try:
                soup = BeautifulSoup(self._get(cfg["index_url"]), "html.parser")
                feeds += [urljoin(cfg["index_url"], a["href"]) for a in soup.find_all("a", href=True) if a["href"].lower().endswith(".rss")]
            except requests.RequestException:
                pass
        urls = []
        for feed in dict.fromkeys(feeds):
            try:
                root = ElementTree.fromstring(self._get(feed))
            except (requests.RequestException, ElementTree.ParseError):
                continue
            for e in root.iter():
                if e.tag.rsplit("}", 1)[-1] == "link":
                    href = e.attrib.get("href") or (e.text or "")
                    if href.strip():
                        urls.append(urljoin(feed, href.strip()))
        return urls

    def _sitemap(self):
        queue = [urljoin(self.source["url"], p) for p in self.source.get("sitemap", {}).get("paths", ["/sitemap.xml"])]
        urls, seen = [], set()
        while queue:
            sm = queue.pop(0)
            if sm in seen:
                continue
            seen.add(sm)
            try:
                root = ElementTree.fromstring(self._get(sm))
            except (requests.RequestException, ElementTree.ParseError):
                continue
            tag = root.tag.rsplit("}", 1)[-1]
            for e in root.iter():
                if e.tag.rsplit("}", 1)[-1] != "loc" or not e.text:
                    continue
                loc = urljoin(sm, e.text.strip())
                (queue if tag == "sitemapindex" else urls).append(loc)
        return urls

    def _normalize(self, urls):
        host = urlparse(self.source["url"]).netloc.lower()
        seen = set()
        now = datetime.now(timezone.utc)
        result = []
        for raw in urls:
            url = self._canonicalize(raw)
            if not url or urlparse(url).netloc.lower() != host or url in seen:
                continue
            seen.add(url)
            result.append(ArticleRef(self.source["id"], url, now))
        return result

    @staticmethod
    def _canonicalize(url):
        try:
            p = urlparse(url)
            if p.scheme not in {"http", "https"} or not p.netloc:
                return None
            return urlunparse((p.scheme, p.netloc, p.path.rstrip("/"), "", "", ""))
        except ValueError:
            return None
