from datetime import datetime
import os
from zoneinfo import ZoneInfo
from .article_pool import ArticlePool
from .config import ROOT, load_settings
from .crawler import article_id, crawl_sources
from .discovery import SourceDiscovery
from .epub import EpubGenerator
from .extractor import ArticleExtractor
from .registry import SourceRegistry
from .validator import validate_epub
from .drive_upload import upload_epub


def _is_today_or_undated(published_at, timezone_name):
    if not published_at:
        return True
    try:
        published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    tz = ZoneInfo(timezone_name)
    today = datetime.now(tz).date()
    if published.tzinfo is None:
        return published.date() == today
    return published.astimezone(tz).date() == today


def run():
    settings = load_settings()
    timezone_name = settings.get("timezone", "Asia/Ho_Chi_Minh")
    registry = SourceRegistry()
    active_sources = [s for s in registry.list_sources() if s.get("status") == "active"]
    output_dir = ROOT / settings.get("storage", {}).get("article_pool", "data/article_pool")
    pool = ArticlePool(output_dir)
    extractor = ArticleExtractor()
    edition_article_ids = []
    crawl_jobs = []
    discovered = {}

    # Discover every source first, then run Scrapy exactly once. Scrapy's
    # reactor is not restartable within the same Python process.
    for source in active_sources:
        try:
            refs = SourceDiscovery(source, settings).discover()
            limit = int(source.get("html", {}).get("max_articles", 20))
            refs = refs[:limit]
            discovered[source["id"]] = refs
            crawl_jobs.append((refs, source))
            print(f"{source['id']}: discovered {len(refs)} article URLs")
        except Exception as exc:
            print(f"{source['id']}: discovery failed: {type(exc).__name__}: {exc!r}")

    if crawl_jobs:
        try:
            crawl_sources(crawl_jobs, settings, output_dir)
        except Exception as exc:
            # Do not hide reactor/crawler failures behind an empty exception string.
            print(f"crawl failed: {type(exc).__name__}: {exc!r}")
            raise

    for source in active_sources:
        refs = discovered.get(source["id"], [])
        kept = dropped_quality = 0
        for ref in refs:
            item_id = article_id(ref.url)
            html_path = pool.html_path(ref.source_id, item_id)
            if not html_path.exists():
                print(f"{source['id']}: crawl missing {ref.url}")
                continue
            try:
                article = extractor.extract(html_path, ref.url, source)
                article["id"] = item_id
                article["source_id"] = ref.source_id
                ok, reason = extractor.quality_check(article, source)
                if not ok:
                    dropped_quality += 1
                    print(f"{source['id']}: quality drop {ref.url}: {reason}")
                    continue
                pool.write_article(article)
                # Publication date is metadata only. Edition selection follows
                # discovery order and the source limit; no date filtering.
                if item_id not in edition_article_ids:
                    edition_article_ids.append(item_id)
                kept += 1
            except Exception as exc:
                print(f"{source['id']}: extraction failed {ref.url}: {type(exc).__name__}: {exc!r}")
        print(f"{source['id']}: edition kept={kept}, dropped_quality={dropped_quality}")

    epub_path = ROOT / settings.get("storage", {}).get("editions", "data/editions") / "0neNews.epub"
    generator = EpubGenerator(timezone=timezone_name)
    generator.generate(
        article_pool=output_dir,
        output_path=epub_path,
        sources=active_sources,
        title=settings.get("edition", {}).get("title", "YOUR NEWS"),
        edition_time=settings.get("edition", {}).get("time", "07:00"),
        article_ids=edition_article_ids,
    )
    size = epub_path.stat().st_size
    print(f"edition size={size} bytes articles={len(edition_article_ids)}")
    validate_epub(epub_path)
    print(f"EPUB validated: {epub_path}")
    if os.getenv("TANGTHU_UPLOAD_ENABLED", "false").strip().lower() == "true":
        result = upload_epub(epub_path, filename=settings.get("drive_upload", {}).get("filename", "0neNews.epub"))
        print(f"Drive upload complete: {result.get('filename','0neNews.epub')} (file_id={result.get('file_id','unknown')}, operation={result.get('operation','unknown')})")
    else:
        print("Drive upload skipped: TANGTHU_UPLOAD_ENABLED is not true.")


if __name__ == "__main__":
    run()
