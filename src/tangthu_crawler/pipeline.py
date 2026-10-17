from .config import ROOT, load_settings
from .crawler import crawl
from .discovery import SourceDiscovery
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


if __name__ == "__main__":
    run()
