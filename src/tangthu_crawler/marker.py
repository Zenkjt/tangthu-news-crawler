from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .config import ROOT


MARKER_SCHEMA_VERSION = 1
VALID_STATUSES = {"pending", "analyzing", "verified", "degraded", "failed"}
VALID_ADAPTERS = {"generic_html", "vnexpress"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _domain(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


class SourceMarkerRegistry:
    """Persistent, per-source profile markers used by the crawler.

    A marker is keyed by source_id (not domain), because different URLs on the
    same website can require different discovery profiles.
    """

    def __init__(self, path: Path | None = None):
        self.path = path or ROOT / "config" / "source_markers.json"
        self.data = self._load()
        self.changed = False

    def _load(self) -> dict:
        if not self.path.exists():
            return {"schema_version": MARKER_SCHEMA_VERSION, "markers": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Cannot read source markers {self.path}: {exc}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("markers"), list):
            raise RuntimeError(f"Invalid source marker registry: {self.path}")
        if data.get("schema_version") != MARKER_SCHEMA_VERSION:
            raise RuntimeError(
                "Unsupported source marker schema version: "
                f"{data.get('schema_version')!r}"
            )
        return data

    def list_markers(self) -> list[dict]:
        return deepcopy(self.data["markers"])

    def get(self, source_id: str) -> dict | None:
        for marker in self.data["markers"]:
            if marker.get("source_id") == source_id:
                return deepcopy(marker)
        return None

    @staticmethod
    def _new_marker(source: dict) -> dict:
        url = str(source.get("url") or "").strip()
        adapter_id = "vnexpress" if source.get("site_adapter") == "vnexpress" else "generic_html"
        now = _utc_now()
        return {
            "source_id": str(source["id"]),
            "source_url": url,
            "domain": _domain(url),
            "adapter_id": adapter_id,
            "adapter_version": "1",
            "profile": {
                "discovery": deepcopy(source.get("discovery", ["html"])),
                "html": deepcopy(source.get("html", {})),
                "extractor": deepcopy(source.get("extractor", {"engine": "trafilatura"})),
                "quality_gate": deepcopy(source.get("quality_gate", {})),
                "http": deepcopy(source.get("http", {})),
            },
            "status": "pending",
            "quality": {
                "score": None,
                "sample_size": 0,
                "passed": None,
            },
            "analysis": {
                "last_analyzed_at": None,
                "note": "Initial marker from the existing crawler profile; awaiting Analyzer verification.",
            },
            "marker_version": 1,
            "created_at": now,
            "updated_at": now,
        }

    def update(
        self,
        source_id: str,
        *,
        adapter_id: str | None = None,
        profile: dict | None = None,
        status: str | None = None,
        quality: dict | None = None,
        analysis: dict | None = None,
    ) -> dict:
        """Update one marker after Analyzer verification."""
        for marker in self.data["markers"]:
            if marker.get("source_id") != source_id:
                continue
            if adapter_id is not None:
                if adapter_id not in VALID_ADAPTERS:
                    raise ValueError(f"Unsupported adapter_id: {adapter_id}")
                marker["adapter_id"] = adapter_id
            if profile is not None:
                marker["profile"] = deepcopy(profile)
            if status is not None:
                if status not in VALID_STATUSES:
                    raise ValueError(f"Unsupported marker status: {status}")
                marker["status"] = status
            if quality is not None:
                marker["quality"] = {**marker.get("quality", {}), **deepcopy(quality)}
            if analysis is not None:
                marker["analysis"] = {**marker.get("analysis", {}), **deepcopy(analysis)}
            marker["marker_version"] = int(marker.get("marker_version", 0)) + 1
            marker["updated_at"] = _utc_now()
            self.changed = True
            return deepcopy(marker)
        raise KeyError(f"Unknown source marker: {source_id}")

    def ensure_sources(self, sources: list[dict]) -> int:
        """Create markers for unseen sources; never overwrite existing decisions."""
        existing = {m.get("source_id") for m in self.data["markers"]}
        added = 0
        for source in sources:
            source_id = str(source.get("id") or "").strip()
            url = str(source.get("url") or "").strip()
            if not source_id or not url or source_id in existing:
                continue
            self.data["markers"].append(self._new_marker(source))
            existing.add(source_id)
            added += 1
        if added:
            self.data["markers"].sort(key=lambda item: item["source_id"])
            self.changed = True
        return added

    def apply(self, source: dict) -> dict:
        """Apply the persisted marker profile to a resolved source config."""
        marker = self.get(str(source.get("id") or ""))
        if marker is None:
            raise KeyError(f"No marker assigned to source {source.get('id')!r}")

        profile = marker.get("profile", {})
        source["discovery"] = deepcopy(profile.get("discovery", ["html"]))
        source["html"] = deepcopy(profile.get("html", {}))
        source["extractor"] = deepcopy(profile.get("extractor", {"engine": "trafilatura"}))
        source["quality_gate"] = deepcopy(profile.get("quality_gate", {}))
        if profile.get("http"):
            source["http"] = deepcopy(profile["http"])

        if marker.get("adapter_id") == "vnexpress":
            source["site_adapter"] = "vnexpress"
        else:
            source.pop("site_adapter", None)
        source["_marker"] = marker
        return source

    def save(self) -> None:
        if not self.changed:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.changed = False
