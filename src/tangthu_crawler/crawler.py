from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import scrapy
from scrapy.crawler import CrawlerProcess

from .models import ArticleRef


def article_id(url: str) -> str:
    """Return the stable ID used for all representations of an article URL."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]


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
        source: dict,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.refs = refs
        self.output_dir = Path(output_dir)
        self.settings_cfg = settings
        self.source = source
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def start(self):
        for ref in self.refs:
            yield scrapy.Request(
                ref.url,
                callback=self.parse_article,
                errback=self.handle_error,
                meta={"source_id": ref.source_id, "article_url": ref.url},
                dont_filter=False,
            )

    def parse_article(self, response):
        url = response.meta["article_url"]
        source_id = response.meta["source_id"]

        if not self._allowed_domain(response.url):
            self.logger.warning("Skipped off-domain URL: %s", response.url)
            return

        item_id = article_id(url)
        target_dir = self.output_dir / source_id
        target_dir.mkdir(parents=True, exist_ok=True)

        html_path = target_dir / f"{item_id}.html"
        meta_path = target_dir / f"{item_id}.meta.json"

        html_path.write_bytes(response.body)

        metadata = {
            "id": item_id,
            "source_id": source_id,
            "url": url,
            "fetched_url": response.url,
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

    def handle_error(self, failure):
        request = failure.request
        self.logger.warning(
            "Crawl failed: %s %s",
            request.meta.get("source_id"),
            request.meta.get("article_url", request.url),
        )

    def _allowed_domain(self, url: str) -> bool:
        configured = urlparse(self.source["url"]).hostname
        actual = urlparse(url).hostname
        if not configured or not actual:
            return False
        return actual == configured or actual.endswith("." + configured)


def crawl(
    refs: list[ArticleRef],
    source: dict,
    settings: dict,
    output_dir: str | Path,
) -> None:
    if not refs:
        return

    crawler_cfg = settings.get("crawler", {})
    process = CrawlerProcess(
        settings={
            "USER_AGENT": crawler_cfg.get(
                "user_agent", "TangThuNewsCrawler/0.1"
            ),
            "DOWNLOAD_TIMEOUT": crawler_cfg.get("request_timeout", 20),
            "CONCURRENT_REQUESTS": crawler_cfg.get("concurrency", 8),
            "RETRY_TIMES": crawler_cfg.get("retry_times", 2),
            "ROBOTSTXT_OBEY": True,
            "LOG_LEVEL": "INFO",
            "COOKIES_ENABLED": False,
            "TELNETCONSOLE_ENABLED": False,
        }
    )
    process.crawl(
        ArticleSpider,
        refs=refs,
        output_dir=output_dir,
        settings=settings,
        source=source,
    )
    process.start()
