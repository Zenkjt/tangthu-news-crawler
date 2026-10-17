from pathlib import Path
from .config import ROOT, load_yaml
class SourceRegistry:
    def __init__(self, source_dir: Path | None = None):
        self.source_dir = source_dir or ROOT / "config" / "sources"
    def list_sources(self) -> list[dict]:
        return [load_yaml(p) for p in sorted(self.source_dir.glob("*.yaml"))]
    def get(self, source_id: str) -> dict:
        path = self.source_dir / f"{source_id}.yaml"
        if not path.exists():
            raise KeyError(f"Unknown source: {source_id}")
        return load_yaml(path)
