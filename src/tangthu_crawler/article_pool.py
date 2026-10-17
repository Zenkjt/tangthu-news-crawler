from __future__ import annotations

import json
from pathlib import Path


class ArticlePool:
    """Read crawled raw HTML files and write normalized Article JSON."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def iter_html(self):
        yield from self.root.glob("*/*.html")

    def write_article(self, article: dict) -> Path:
        source_id = article["source_id"]
        filename = article["id"]
        target = self.root / source_id / f"{filename}.json"
        target.write_text(
            json.dumps(article, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target
