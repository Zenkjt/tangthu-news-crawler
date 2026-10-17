from .article_pool import ArticlePool
from .config import ROOT, load_settings
from .crawler import article_id, crawl
from .discovery import SourceDiscovery
from .epub import EpubGenerator
from .extractor import ArticleExtractor
from .registry import SourceRegistry


def run() -> None:
    settings = load_settings()
    registry = SourceRegistry()
    active_sources = [
        source
        for source in registry.list_sources()
        if source.get("status") == "active"
    ]

    output_dir = ROOT / settings.get("storage", {}).get(
        "article_pool", "data/article_pool"
    )

    for source in active_sources:
        refs = SourceDiscovery(source, settings).discover()
        print(f"{source['id']}: discovered {len(refs)} article URLs")

        crawl(refs, source, settings, output_dir)

        extractor = ArticleExtractor()
        pool = ArticlePool(output_dir)

        for ref in refs:
            item_id = article_id(ref.url)
            html_path = pool.html_path(ref.source_id, item_id)

            if not html_path.exists():
                print(f"{source['id']}: crawl missing {ref.url}")
                continue

            try:
                article = extractor.extract(html_path, ref.url)
            except Exception as exc:
                print(f"{source['id']}: extraction failed {ref.url}: {exc}")
                continue

            article["id"] = item_id
            article["source_id"] = ref.source_id
            pool.write_article(article)

    epub_path = ROOT / settings.get("storage", {}).get(
        "epub", "data/editions/0neNews.epub"
    )
    EpubGenerator().generate(
        article_pool=output_dir,
        output_path=epub_path,
        sources=active_sources,
        title=settings.get("edition", {}).get("title", "YOUR NEWS"),
        edition_time=settings.get("edition", {}).get("time", "07:00"),
    )
    print(f"EPUB generated: {epub_path}")


if __name__ == "__main__":
    run()
