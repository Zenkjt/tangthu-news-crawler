from .article_pool import ArticlePool
from .config import ROOT, load_settings
from .crawler import article_id, crawl
from .discovery import SourceDiscovery
from .extractor import ArticleExtractor
from .registry import SourceRegistry


def run() -> None:
    settings = load_settings()
    registry = SourceRegistry()

    for source in registry.list_sources():
        if source.get("status") != "active":
            continue

        refs = SourceDiscovery(source, settings).discover()
        print(f"{source['id']}: discovered {len(refs)} article URLs")

        output_dir = ROOT / settings.get("storage", {}).get(
            "article_pool", "data/article_pool"
        )
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


if __name__ == "__main__":
    run()
