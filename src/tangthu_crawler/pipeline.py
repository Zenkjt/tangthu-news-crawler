from .article_pool import ArticlePool
from .config import ROOT, load_settings
from .crawler import crawl
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
            html_path = pool.root / ref.source_id
            matches = list(html_path.glob("*.html"))
            # The crawler names files from the URL hash; find the matching file
            # without duplicating URL hashing logic in the pipeline.
            for raw_file in matches:
                try:
                    article = extractor.extract(raw_file, ref.url)
                except Exception as exc:
                    print(f"{source['id']}: extraction failed {ref.url}: {exc}")
                    continue

                article["source_id"] = ref.source_id
                article["id"] = raw_file.stem
                pool.write_article(article)
                break


if __name__ == "__main__":
    run()
