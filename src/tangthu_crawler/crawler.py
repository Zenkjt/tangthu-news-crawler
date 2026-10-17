from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse

import scrapy
from scrapy.crawler import CrawlerProcess

from .models import ArticleRef


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

    def start_requests(self):
        for ref in self.refs:
            yield scrapy.Request(
                ref.url,
                callback=self.parse_article,
                errback=self.handle_error,
                meta={"source_id": ref.source_id, "article_url": ref.url},
                dont_filter=False,
            )

    def parse_article(self, response):
        url = response.url
        source_id = response.meta["source_id"]

        if not self._allowed_domain(url):
            self.logger.warning("Skipped off-domain URL: %s", url)
            return

        filename = self._filename(url)
        target = self.output_dir / source_id / f"{filename}.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.body)

        yield {
            "source_id": source_id,
            "url": url,
            "status": response.status,
            "content_type": response.headers.get(b"Content-Type", b"").decode(
                "latin-1", errors="replace"
            ),
            "path": str(target),
        }

    def handle_error(self, failure):
        request = failure.request
        self.logger.warning(
            "Crawl failed: %s %s",
            request.meta.get("source_id"),
            request.url,
        )

    def _allowed_domain(self, url: str) -> bool:
        configured = urlparse(self.source["url"]).hostname
        actual = urlparse(url).hostname
        if not configured or not actual:
            return False
        return actual == configured or actual.endswith("." + configured)

    @staticmethod
    def _filename(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]


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
