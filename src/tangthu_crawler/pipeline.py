from .registry import SourceRegistry
def run() -> None:
    sources = SourceRegistry().list_sources()
    print(f"Registered sources: {len(sources)}")
    for source in sources:
        print(f"- {source['id']}: {source['name']} [{source['status']}]")
