from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]
def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
def load_settings() -> dict:
    return load_yaml(ROOT / "config" / "settings.yaml")
def load_source(source_id: str) -> dict:
    return load_yaml(ROOT / "config" / "sources" / f"{source_id}.yaml")
