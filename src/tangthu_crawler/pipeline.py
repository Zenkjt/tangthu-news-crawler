from datetime import datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo
from .article_pool import ArticlePool
from .config import ROOT, load_settings
from .crawler import article_id, crawl
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


def _build_with_size_cap(generator, article_pool, output_path, sources, title, edition_time, article_ids, max_bytes):
    """Keep the newest articles while enforcing a hard EPUB size budget."""
    pool = Path(article_pool)
    records = []
    for path in pool.glob("*/*.json"):
        if path.name.endswith(".meta.json"):
            continue
        try:
            article = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if article.get("id") not in article_ids:
            continue
        records.append((article.get("published_at") or "", article.get("id")))
    records.sort(key=lambda item: item[0], reverse=True)
    ordered = [item[1] for item in records]
    while True:
        generator.generate(
            article_pool=article_pool,
            output_path=output_path,
            sources=sources,
            title=title,
            edition_time=edition_time,
            article_ids=set(ordered),
        )
        size = output_path.stat().st_size
        if size <= max_bytes or len(ordered) <= 1:
            print(f"edition size={size} bytes cap={max_bytes} articles={len(ordered)}")
            if size > max_bytes:
                print("edition size cap could not be met with a single article")
            return
        # Remove the oldest remaining article first; the newest stay in the edition.
        ordered.pop()


def run():
    settings = load_settings()
    timezone_name = settings.get("timezone", "Asia/Ho_Chi_Minh")
    registry = SourceRegistry()
    active_sources = [s for s in registry.list_sources() if s.get("status") == "active"]
    output_dir = ROOT / settings.get("storage", {}).get("article_pool", "data/article_pool")
    pool = ArticlePool(output_dir)
    extractor = ArticleExtractor()
    edition_article_ids = set()

    for source in active_sources:
        try:
            refs = SourceDiscovery(source, settings).discover()
            limit = int(source.get("html", {}).get("max_articles", 20))
            refs = refs[:limit]
            print(f"{source['id']}: discovered {len(refs)} article URLs")
        except Exception as exc:
            print(f"{source['id']}: discovery failed: {exc}")
            continue
        try:
            crawl(refs, source, settings, output_dir)
        except Exception as exc:
            print(f"{source['id']}: crawl failed: {exc}")
            continue
        kept = dropped_old = dropped_quality = 0
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
                if _is_today_or_undated(article.get("published_at"), timezone_name):
                    edition_article_ids.add(item_id)
                    kept += 1
                else:
                    dropped_old += 1
            except Exception as exc:
                print(f"{source['id']}: extraction failed {ref.url}: {exc}")
        print(f"{source['id']}: edition kept={kept}, dropped_old={dropped_old}, dropped_quality={dropped_quality}")

    epub_path = ROOT / settings.get("storage", {}).get("editions", "data/editions") / "0neNews.epub"
    max_bytes = int(settings.get("edition", {}).get("max_epub_bytes", 1572864))
    generator = EpubGenerator(timezone=timezone_name)
    _build_with_size_cap(
        generator,
        output_dir,
        epub_path,
        active_sources,
        settings.get("edition", {}).get("title", "YOUR NEWS"),
        settings.get("edition", {}).get("time", "07:00"),
        edition_article_ids,
        max_bytes,
    )
    validate_epub(epub_path)
    print(f"EPUB validated: {epub_path}")
    if os.getenv("TANGTHU_UPLOAD_ENABLED", "false").strip().lower() == "true":
        result = upload_epub(epub_path, filename=settings.get("drive_upload", {}).get("filename", "0neNews.epub"))
        print(f"Drive upload complete: {result.get('filename','0neNews.epub')} (file_id={result.get('file_id','unknown')}, operation={result.get('operation','unknown')})")
    else:
        print("Drive upload skipped: TANGTHU_UPLOAD_ENABLED is not true.")


if __name__ == "__main__":
    run()
