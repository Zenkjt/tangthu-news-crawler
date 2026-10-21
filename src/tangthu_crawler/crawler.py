from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import scrapy
from bs4 import BeautifulSoup
from scrapy.crawler import CrawlerProcess

from .models import ArticleRef


DEFAULT_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "vi,en-US;q=0.8,en;q=0.6",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

PAGINATION_HREF_RE = re.compile(
    r"(?:[?&](?:page|p)=\d+|[-_/](?:page|p)[-_]?\d+(?:\D|$)|/(?:\d+)(?:$|[?#]))",
    re.I,
)
PAGINATION_TEXT_RE = re.compile(
    r"^(?:next|next page|trang\s+\d+|\d+|›|»|→|>)$",
    re.I,
)
PAGINATION_WORD_RE = re.compile(r"\b(?:next|trang)\b", re.I)


def article_id(url: str) -> str:
    """Return the stable ID used for all representations of an article URL."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]


def build_crawler_settings(settings: dict, source: dict | None = None) -> dict:
    crawler_cfg = settings.get("crawler", {})
    source_http = (source or {}).get("http", {})

    headers = dict(DEFAULT_REQUEST_HEADERS)
    headers.update(source_http.get("headers", {}))

    return {
        "USER_AGENT": crawler_cfg.get("user_agent", DEFAULT_BROWSER_USER_AGENT),
        "DEFAULT_REQUEST_HEADERS": headers,
        "DOWNLOAD_TIMEOUT": crawler_cfg.get("request_timeout", 20),
        "CONCURRENT_REQUESTS": crawler_cfg.get("concurrency", 1),
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": crawler_cfg.get("download_delay", 2),
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": crawler_cfg.get("autothrottle_start_delay", 2),
        "AUTOTHROTTLE_MAX_DELAY": crawler_cfg.get("autothrottle_max_delay", 10),
        "AUTOTHROTTLE_TARGET_CONCURRENCY": crawler_cfg.get("autothrottle_target_concurrency", 0.5),
        "RETRY_TIMES": crawler_cfg.get("retry_times", 2),
        "RETRY_HTTP_CODES": [408, 429, 500, 502, 503, 504, 522, 524],
        "ROBOTSTXT_OBEY": True,
        "LOG_LEVEL": "INFO",
        "COOKIES_ENABLED": False,
        "TELNETCONSOLE_ENABLED": False,
    }


class ArticleSpider(scrapy.Spider):
    name = "tangthu_article"

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "LOG_LEVEL": "INFO",
        "COOKIES_ENABLED": False,
    }

    def __init__(
        self,
        refs: list[ArticleRef],
        output_dir: str | Path,
        settings: dict,
        source: dict | None = None,
        source_map: dict | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.refs = refs
        self.output_dir = Path(output_dir)
        self.settings_cfg = settings
        self.source = source or {}
        self.source_map = source_map or {}
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def start(self):
        for ref in self.refs:
            source = self.source_map.get(ref.source_id, self.source) or {}
            headers = dict(source.get("http", {}).get("headers", {}))
            yield scrapy.Request(
                ref.url,
                callback=self.parse_article,
                errback=self.handle_error,
                headers=headers,
                meta={
                    "source_id": ref.source_id,
                    "article_url": ref.url,
                    "root_url": ref.url,
                    "root_id": article_id(ref.url),
                    "page_index": 1,
                },
                dont_filter=False,
            )

    def parse_article(self, response):
        url = response.meta["article_url"]
        root_url = response.meta["root_url"]
        source_id = response.meta["source_id"]
        root_id = response.meta["root_id"]
        page_index = int(response.meta.get("page_index", 1))

        if not self._allowed_domain(response.url, source_id):
            self.logger.warning("Skipped off-domain URL: %s", response.url)
            return

        target_dir = self.output_dir / source_id
        target_dir.mkdir(parents=True, exist_ok=True)

        # A recrawl of page 1 must invalidate stale continuation pages.
        # Otherwise an old page2 can be accidentally merged into a new article.
        if page_index == 1:
            for stale in target_dir.glob(f"{root_id}.page*.html"):
                stale.unlink(missing_ok=True)
            for stale in target_dir.glob(f"{root_id}.page*.meta.json"):
                stale.unlink(missing_ok=True)

        suffix = "" if page_index == 1 else f".page{page_index}"
        html_path = target_dir / f"{root_id}{suffix}.html"
        meta_path = target_dir / f"{root_id}{suffix}.meta.json"

        html_path.write_bytes(response.body)

        metadata = {
            "id": root_id,
            "source_id": source_id,
            "url": root_url,
            "page_url": response.url,
            "page_index": page_index,
            "status": response.status,
            "content_type": response.headers.get(
                b"Content-Type", b""
            ).decode("latin-1", errors="replace"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "html_path": str(html_path),
        }
        meta_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        yield metadata

        pagination = self._pagination_config(source_id)
        max_pages = max(1, int(pagination.get("max_pages", 5)))
        if pagination.get("enabled", True) is False or page_index >= max_pages:
            return

        next_url = self._find_next_page(
            response,
            root_url=root_url,
            page_index=page_index,
        )
        if not next_url:
            return

        yield scrapy.Request(
            next_url,
            callback=self.parse_article,
            errback=self.handle_error,
            headers=dict(
                (self.source_map.get(source_id, self.source) or {})
                .get("http", {})
                .get("headers", {})
            ),
            meta={
                "source_id": source_id,
                "article_url": root_url,
                "root_url": root_url,
                "root_id": root_id,
                "page_index": page_index + 1,
            },
            dont_filter=False,
        )

    def handle_error(self, failure):
        request = failure.request
        self.logger.warning(
            "Crawl failed: source=%s url=%s type=%s error=%r",
            request.meta.get("source_id"),
            request.meta.get("article_url", request.url),
            type(failure.value).__name__,
            failure.value,
        )

    def _pagination_config(self, source_id: str) -> dict:
        source = self.source_map.get(source_id, self.source) or {}
        return source.get("pagination", {})

    def _find_next_page(self, response, *, root_url: str, page_index: int) -> str | None:
        soup = BeautifulSoup(response.text, "html.parser")
        candidates = []

        for position, anchor in enumerate(soup.find_all("a", href=True)):
            href = anchor.get("href", "").strip()
            if not href:
                continue

            candidate = urljoin(response.url, href)
            if not self._same_domain(candidate, root_url):
                continue
            if candidate.rstrip("#") == response.url.rstrip("#"):
                continue
            if not self._same_article(candidate, root_url):
                continue

            candidate_page = self._page_number(candidate, root_url)
            # Do not assume that page1 is the first page.  Some sites use:
            #   article.html       -> first page
            #   article-page0.html
            #   article-page1.html
            # and so on.  A numeric pagination URL is therefore a valid
            # continuation regardless of its number.  The current response
            # URL and the root URL are excluded to prevent cycles.
            if candidate.rstrip("#") == root_url.rstrip("#"):
                continue

            rel = {str(value).casefold() for value in anchor.get("rel", [])}
            text = " ".join(anchor.stripped_strings)

            score = 0
            if "next" in rel:
                score += 10
            if PAGINATION_TEXT_RE.match(text):
                score += 7
            if PAGINATION_WORD_RE.search(text):
                score += 5
            if PAGINATION_HREF_RE.search(candidate):
                score += 6
            if anchor.find_parent(["article", "main"]):
                score += 2

            if score:
                candidates.append((score, -position, candidate))

        if not candidates:
            return None

        current_page = self._page_number(response.url, root_url)
        if current_page is None:
            # The root article URL is the physical first page, but it has no
            # numeric suffix. Treat it as -1 so page0 remains a valid
            # continuation candidate.
            current_page = -1

        # Prefer an explicit next link first. Otherwise walk numeric pages in
        # ascending order, allowing page0/page1/... regardless of the site's
        # numbering convention. If no numeric candidate is available, fall
        # back to the scored candidate.
        next_candidates = [item for item in candidates if item[0] >= 10]
        if next_candidates:
            next_candidates.sort(reverse=True)
            return next_candidates[0][2]

        numeric_candidates = [
            item for item in candidates
            if self._page_number(item[2], root_url) is not None
            and self._page_number(item[2], root_url) != current_page
        ]
        if numeric_candidates:
            numeric_candidates.sort(
                key=lambda item: (
                    self._page_number(item[2], root_url),
                    -item[0],
                    item[1],
                )
            )
            return numeric_candidates[0][2]

        candidates.sort(reverse=True)
        return candidates[0][2]

    @staticmethod
    def _same_domain(candidate: str, root_url: str) -> bool:
        root_host = (urlparse(root_url).hostname or "").lower()
        host = (urlparse(candidate).hostname or "").lower()
        return bool(
            root_host
            and host
            and (host == root_host or host.endswith("." + root_host))
        )

    @staticmethod
    def _article_identity(url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/").lower()
        extension = ""
        if path.endswith(".html"):
            path = path[:-5]
            extension = ".html"
        path = re.sub(r"[-_/](?:page|p)[-_]?\d+$", "", path)
        path = re.sub(r"/\d+$", "", path)
        return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}{extension}"

    @classmethod
    def _same_article(cls, candidate: str, root_url: str) -> bool:
        if cls._article_identity(candidate) == cls._article_identity(root_url):
            return True

        root = urlparse(root_url)
        other = urlparse(candidate)
        root_path = root.path.rstrip("/").lower()
        other_path = other.path.rstrip("/").lower()

        if root_path.endswith(".html"):
            root_path = root_path[:-5]
        if other_path.endswith(".html"):
            other_path = other_path[:-5]

        if other_path.startswith(root_path + "/"):
            suffix = other_path[len(root_path) + 1:]
            return suffix.isdigit()

        if other_path.startswith(root_path + "-") or other_path.startswith(root_path + "_"):
            suffix = other_path[len(root_path) + 1:]
            return suffix.isdigit()

        return False

    @staticmethod
    def _page_number(url: str, root_url: str) -> int | None:
        parsed = urlparse(url)
        query_match = re.search(
            r"(?:^|&)(?:page|p)=(\d+)(?:&|$)",
            parsed.query,
            re.I,
        )
        if query_match:
            return int(query_match.group(1))

        path = parsed.path.rstrip("/").lower()
        match = re.search(
            r"(?:[-_/](?:page|p)[-_]?/?|/)(\d+)(?:\.html)?$",
            path,
            re.I,
        )
        if match:
            return int(match.group(1))

        root = urlparse(root_url)
        root_path = root.path.rstrip("/").lower()
        if root_path.endswith(".html"):
            root_path = root_path[:-5]
        candidate_path = path[:-5] if path.endswith(".html") else path

        for separator in ("-", "_", "/"):
            prefix = root_path + separator
            if candidate_path.startswith(prefix):
                suffix = candidate_path[len(prefix):]
                if suffix.isdigit():
                    return int(suffix)

        return None

    def _allowed_domain(self, url: str, source_id: str | None = None) -> bool:
        source = self.source_map.get(source_id, self.source) or {}
        configured = urlparse(source.get("url", "")).hostname
        actual = urlparse(url).hostname
        if not configured or not actual:
            return False
        return actual == configured or actual.endswith("." + configured)


def crawl_sources(
    jobs: list[tuple[list[ArticleRef], dict]],
    settings: dict,
    output_dir: str | Path,
) -> None:
    """Crawl all active sources in one Scrapy reactor run.

    Scrapy's reactor cannot be restarted in the same Python process, so the
    pipeline must schedule every source before calling process.start().
    """
    refs = []
    source_map = {}
    for source_refs, source in jobs:
        refs.extend(source_refs)
        source_map[source["id"]] = source
    if not refs:
        return

    process = CrawlerProcess(settings=build_crawler_settings(settings))
    process.crawl(
        ArticleSpider,
        refs=refs,
        output_dir=output_dir,
        settings=settings,
        source_map=source_map,
    )
    process.start()


def crawl(
    refs: list[ArticleRef],
    source: dict,
    settings: dict,
    output_dir: str | Path,
) -> None:
    """Backward-compatible single-source entry point.

    New code should use crawl_sources() when processing multiple sources.
    """
    crawl_sources([(refs, source)], settings, output_dir)
