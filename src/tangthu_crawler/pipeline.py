from .config import load_settings
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
        for ref in refs[:10]:
            print(f"  {ref.url}")


if __name__ == "__main__":
    run()
