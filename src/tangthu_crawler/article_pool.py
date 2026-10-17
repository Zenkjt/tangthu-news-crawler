from __future__ import annotations

import json
from pathlib import Path


class ArticlePool:
    """Persist and retrieve raw crawl metadata and normalized articles."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def metadata_path(self, source_id: str, article_id: str) -> Path:
        return self.root / source_id / f"{article_id}.meta.json"

    def html_path(self, source_id: str, article_id: str) -> Path:
        return self.root / source_id / f"{article_id}.html"

    def article_path(self, source_id: str, article_id: str) -> Path:
        return self.root / source_id / f"{article_id}.json"

    def read_metadata(self, source_id: str, article_id: str) -> dict:
        path = self.metadata_path(source_id, article_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def write_article(self, article: dict) -> Path:
        target = self.article_path(article["source_id"], article["id"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(article, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target
