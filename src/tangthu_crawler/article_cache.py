from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

DEFAULT_TTL_DAYS = 5


def _parse_dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return _parse_dt(dt).isoformat().replace("+00:00", "Z")


def _safe_key(source_id: str, canonical_url: str) -> str:
    raw = f"{source_id}\n{canonical_url}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass
class ArticleCache:
    root: Path
    ttl_days: int = DEFAULT_TTL_DAYS

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, source_id: str, canonical_url: str) -> Path:
        return self.root / source_id / f"{_safe_key(source_id, canonical_url)}.json"

    def upsert(self, article: dict[str, Any], *, fetched_at: str | datetime | None = None) -> dict[str, Any]:
        """Insert/replace by (source_id, canonical_url); fetched_at resets the 5-day TTL."""
        source_id = str(article["source_id"]).strip()
        canonical_url = str(article["canonical_url"]).strip()
        if not source_id or not canonical_url:
            raise ValueError("source_id and canonical_url are required")

        fetched = _parse_dt(fetched_at or article.get("fetched_at") or datetime.now(timezone.utc))
        record = dict(article)
        record["source_id"] = source_id
        record["canonical_url"] = canonical_url
        record["fetched_at"] = _iso(fetched)
        record["expires_at"] = _iso(fetched + timedelta(days=self.ttl_days))

        path = self._path(source_id, canonical_url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return record

    def get(self, source_id: str, canonical_url: str, *, now: str | datetime | None = None,
            include_expired: bool = False) -> dict[str, Any] | None:
        path = self._path(source_id, canonical_url)
        if not path.exists():
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        if not include_expired and not self._is_live(record, now=now):
            return None
        return record

    def valid_articles(self, source_id: str, *, now: str | datetime | None = None,
                       edition_mode: str = "text") -> list[dict[str, Any]]:
        now_dt = _parse_dt(now or datetime.now(timezone.utc))
        source_dir = self.root / source_id
        if not source_dir.exists():
            return []

        articles: list[dict[str, Any]] = []
        for path in sorted(source_dir.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not self._is_live(record, now=now_dt):
                continue
            if edition_mode == "images" and not self._has_images(record):
                continue
            articles.append(record)

        articles.sort(key=lambda x: (
            x.get("published_at") or "",
            x.get("discovered_at") or "",
            x.get("fetched_at") or "",
        ), reverse=True)
        return articles

    def valid_count(self, source_id: str, *, now: str | datetime | None = None,
                    edition_mode: str = "text") -> int:
        return len(self.valid_articles(source_id, now=now, edition_mode=edition_mode))

    def cleanup_expired(self, *, now: str | datetime | None = None) -> int:
        now_dt = _parse_dt(now or datetime.now(timezone.utc))
        removed = 0
        for path in self.root.glob("*/*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if self._is_expired(record, now_dt):
                try:
                    path.unlink()
                    removed += 1
                except FileNotFoundError:
                    pass

        for source_dir in self.root.iterdir():
            if source_dir.is_dir():
                try:
                    source_dir.rmdir()
                except OSError:
                    pass
        return removed

    def all_records(self, source_id: str, *, include_expired: bool = False,
                    now: str | datetime | None = None) -> list[dict[str, Any]]:
        source_dir = self.root / source_id
        if not source_dir.exists():
            return []
        records = []
        for path in sorted(source_dir.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if include_expired or self._is_live(record, now=now):
                records.append(record)
        return records

    @staticmethod
    def _has_images(record: dict[str, Any]) -> bool:
        images = record.get("images")
        if images is None:
            return bool(record.get("image"))
        if isinstance(images, str):
            return bool(images.strip())
        return isinstance(images, Iterable) and any(images)

    @staticmethod
    def _is_expired(record: dict[str, Any], now: str | datetime) -> bool:
        expires_at = record.get("expires_at")
        if not expires_at:
            return True
        return _parse_dt(now) >= _parse_dt(expires_at)

    @classmethod
    def _is_live(cls, record: dict[str, Any], *, now: str | datetime | None = None) -> bool:
        return not cls._is_expired(record, _parse_dt(now or datetime.now(timezone.utc)))
