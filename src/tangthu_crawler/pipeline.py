from __future__ import annotations

import json
import os
import shutil
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from .article_cache import ArticleCache
from .article_pool import ArticlePool
from .config import ROOT, load_settings
from .crawl_planner import CrawlPlanner
from .crawler import article_id, crawl_sources
from .discovery import SourceDiscovery
from .epub import EpubGenerator
from .extractor import ArticleExtractor
from .models import ArticleRef
from .registry import SourceRegistry
from .validator import validate_epub
from .drive_upload import upload_epub


def _parse_dt(value: str | datetime) -> datetime:
    result = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _canonical_url(value: str) -> str:
    parsed = urlparse(str(value).strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid URL: {value!r}")
    return urlunparse(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), "", "", "")
    )


def _fetch_news_config(settings: dict) -> dict:
    endpoint = (
        os.getenv("TANGTHU_NEWS_CONFIG_URL")
        or settings.get("news", {}).get("config_url")
        or "https://tangthu-news-worker.mienluonngon.workers.dev/news/config"
    )
    request = urllib.request.Request(
        endpoint,
        headers={
            "Accept": "application/json",
            "User-Agent": "TangThu-News-Crawler/2.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot load News Worker registry: {exc}") from exc

    if payload.get("ok") is not True:
        raise RuntimeError(
            f"News Worker registry returned error: {payload.get('error', 'unknown error')}"
        )
    for key in ("branches", "sources", "subscriptions"):
        if not isinstance(payload.get(key), list):
            raise RuntimeError(f"News Worker response has invalid '{key}'")
    return payload


def _resolve_sources(
    registry_sources: list[dict],
    local_sources: list[dict],
) -> tuple[list[dict], dict[str, dict]]:
    """Map Bulletin Registry IDs to local extraction rules by normalized URL/host."""
    by_url: dict[str, dict] = {}
    by_host: dict[str, dict] = {}

    for local in local_sources:
        try:
            by_url[_canonical_url(local["url"])] = local
            host = (urlparse(local["url"]).hostname or "").lower()
            if host:
                by_host.setdefault(host, local)
        except (KeyError, ValueError):
            continue

    resolved: list[dict] = []
    source_map: dict[str, dict] = {}

    for registered in sorted(
        registry_sources,
        key=lambda s: (int(s.get("order", 0)), str(s.get("id", ""))),
    ):
        if registered.get("enabled", True) is False:
            continue

        source_id = str(registered.get("id") or "").strip()
        try:
            url = _canonical_url(str(registered.get("url") or ""))
        except ValueError:
            print(f"Skipping registry source with invalid URL: {registered!r}")
            continue
        if not source_id:
            continue

        local = by_url.get(url)
        if local is None:
            host = (urlparse(url).hostname or "").lower()
            local = by_host.get(host)

        if local:
            config = dict(local)
            config["html"] = dict(local.get("html", {}))
            config["id"] = source_id
            config["name"] = registered.get("name") or url
            config["url"] = url
            config["status"] = "active"
            config.setdefault("policy", {"mode": "excerpt"})
        else:
            # A new host has no source-specific rules yet. Use generic discovery
            # and an excerpt-only policy as the conservative default.
            config = {
                "id": source_id,
                "name": registered.get("name") or url,
                "url": url,
                "status": "active",
                "discovery": ["html"],
                "html": {
                    "strategy": "generic",
                    "max_articles": 20,
                    "min_link_score": 4,
                },
                "extractor": {"engine": "newspaper4k"},
                "quality_gate": {
                    "enabled": True,
                    "require_title": True,
                    "min_body_chars": 300,
                    "min_paragraphs": 2,
                    "reject_titles": ["Untitled", "Article"],
                },
                "policy": {"mode": "excerpt"},
            }

        config["_registry_order"] = int(registered.get("order", 0))
        resolved.append(config)
        source_map[source_id] = config

    return resolved, source_map


def _active_subscriptions(payload: dict, branch_id: str | None = None) -> list[dict]:
    active_branches = {
        b["id"]
        for b in payload["branches"]
        if b.get("id")
        and b.get("enabled", True) is not False
        and b.get("status", "active") == "active"
    }
    active_sources = {
        s["id"]
        for s in payload["sources"]
        if s.get("id") and s.get("enabled", True) is not False
    }

    active = []
    for sub in payload["subscriptions"]:
        if sub.get("enabled", True) is False:
            continue
        if sub.get("branch_id") not in active_branches:
            continue
        if sub.get("source_id") not in active_sources:
            continue
        if branch_id and sub.get("branch_id") != branch_id:
            continue
        active.append(sub)
    return active


def _edition_limits(subscriptions: list[dict]) -> None:
    for branch in sorted({s["branch_id"] for s in subscriptions}):
        branch_subs = [s for s in subscriptions if s["branch_id"] == branch]
        mode = "images" if any(s.get("edition_mode") == "images" for s in branch_subs) else "text"
        count = sum(int(s.get("article_count", 0)) for s in branch_subs)
        limit = 100 if mode == "images" else 200
        if count > limit:
            raise RuntimeError(
                f"Branch {branch} requests {count} articles; {mode} edition limit is {limit}."
            )


def _discover_and_crawl(
    source_map: dict[str, dict],
    decisions,
    settings: dict,
    article_pool: ArticlePool,
    cache: ArticleCache,
) -> None:
    """Discover/fetch only Planner-selected sources, then upsert normalized articles."""
    now = datetime.now(timezone.utc)
    jobs = []
    refs_by_source: dict[str, list[ArticleRef]] = {}

    for decision in decisions:
        if decision.action != "crawl":
            continue
        source = source_map.get(decision.source_id)
        if source is None:
            raise RuntimeError(
                f"Planner selected source {decision.source_id}, but it has no resolved config."
            )

        refs = SourceDiscovery(source, settings).discover()
        # On-demand crawling supplements cache, so skip URLs already usable in
        # this edition mode. Daily decisions intentionally crawl every subscribed
        # source and may refresh URLs that were cached previously.
        if decision.reason == "valid cache is insufficient":
            cached_urls = {
                item.get("canonical_url")
                for item in cache.valid_articles(
                    decision.source_id, edition_mode=decision.edition_mode
                )
            }
            refs = [ref for ref in refs if _canonical_url(ref.url) not in cached_urls]
        limit = max(
            int(source.get("html", {}).get("max_articles", 20)),
            int(decision.missing_count or decision.target_count),
        )
        refs = refs[:limit]
        refs_by_source[decision.source_id] = refs
        jobs.append((refs, source))
        print(
            f"{decision.source_id}: discovered={len(refs)}, "
            f"cache={decision.valid_cached_count}, target={decision.target_count}"
        )

    # All selected source jobs run in one Scrapy reactor session.
    if jobs:
        crawl_sources(jobs, settings, article_pool.root)

    extractor = ArticleExtractor()
    for source_id, refs in refs_by_source.items():
        source = source_map[source_id]
        kept = 0

        for ref in refs:
            item_id = article_id(ref.url)
            html_path = article_pool.html_path(source_id, item_id)
            if not html_path.exists():
                print(f"{source_id}: crawl did not produce HTML for {ref.url}")
                continue

            try:
                article = extractor.extract(html_path, ref.url, source)
                article["id"] = item_id
                article["source_id"] = source_id
                article["canonical_url"] = _canonical_url(
                    article.get("canonical_url") or ref.url
                )
                article["url"] = article.get("url") or ref.url
                article["discovered_at"] = ref.discovered_at.isoformat()

                fetched_at = now
                metadata_path = article_pool.metadata_path(source_id, item_id)
                if metadata_path.exists():
                    try:
                        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                        fetched_at = _parse_dt(metadata.get("fetched_at") or now)
                    except (OSError, json.JSONDecodeError, ValueError):
                        pass
                article["fetched_at"] = fetched_at.isoformat().replace("+00:00", "Z")

                ok, reason = extractor.quality_check(article, source)
                if not ok:
                    print(f"{source_id}: quality drop {ref.url}: {reason}")
                    continue

                article_pool.write_article(article)
                cache.upsert(article, fetched_at=fetched_at)
                kept += 1
            except Exception as exc:
                print(
                    f"{source_id}: extraction failed {ref.url}: "
                    f"{type(exc).__name__}: {exc!r}"
                )

        print(f"{source_id}: cache upserted {kept} qualified articles")


def _select_branch_articles(
    branch_id: str,
    subscriptions: list[dict],
    cache: ArticleCache,
    source_map: dict[str, dict],
) -> tuple[list[dict], list[dict]]:
    mode = "images" if any(s.get("edition_mode") == "images" for s in subscriptions) else "text"
    cap = 100 if mode == "images" else 200
    selected: list[dict] = []
    edition_sources: list[dict] = []
    seen: set[tuple[str, str]] = set()

    source_order = {
        source["id"]: int(source.get("_registry_order", 0))
        for source in source_map.values()
    }
    ordered_subs = sorted(
        subscriptions,
        key=lambda s: (source_order.get(s["source_id"], 10**9), s["source_id"]),
    )

    for sub in ordered_subs:
        source_id = sub["source_id"]
        source = source_map.get(source_id)
        if source is None:
            raise RuntimeError(f"Subscription references unresolved source {source_id}")
        if source_id not in {s["id"] for s in edition_sources}:
            edition_sources.append(source)

        need = int(sub.get("article_count", 5))
        cached = cache.valid_articles(
            source_id,
            edition_mode=mode,
        )
        # If a URL is still present in this source's local crawl list and the
        # fresh extraction passed quality checks, cache.upsert refreshes it.
        # Publication date is intentionally not used for selection. Newest
        # discovery/fetch first, with a deterministic tie-breaker per source.
        cached.sort(
            key=lambda a: (
                a.get("discovered_at") or "",
                a.get("fetched_at") or "",
                a.get("canonical_url") or "",
            ),
            reverse=True,
        )

        added_for_source = 0
        for article in cached:
            identity = (source_id, article.get("canonical_url") or "")
            if identity in seen:
                continue
            seen.add(identity)
            selected.append(article)
            added_for_source += 1
            if added_for_source >= need or len(selected) >= cap:
                break

        print(f"{branch_id}: {source_id} selected={added_for_source}/{need}")
        if len(selected) >= cap:
            selected = selected[:cap]
            break

    return selected, edition_sources


def _write_edition(
    branch_id: str,
    subscriptions: list[dict],
    cache: ArticleCache,
    source_map: dict[str, dict],
    settings: dict,
    *,
    upload: bool,
) -> Path | None:
    if not subscriptions:
        print(f"{branch_id}: no active subscriptions; leave existing Drive EPUB untouched")
        return None

    selected, edition_sources = _select_branch_articles(
        branch_id, subscriptions, cache, source_map
    )
    if not selected:
        print(f"{branch_id}: no valid cached articles; skipping EPUB build/upload")
        return None

    storage = settings.get("storage", {})
    pool_root = (
        ROOT / storage.get("edition_pool", "data/edition_pool") / branch_id
    )
    shutil.rmtree(pool_root, ignore_errors=True)

    selected_ids = []
    for index, article in enumerate(selected, 1):
        source_id = article["source_id"]
        identifier = article.get("id") or article_id(article["canonical_url"])
        item = dict(article)
        item["id"] = identifier
        target = pool_root / source_id / f"{identifier}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        selected_ids.append(identifier)

    edition_dir = ROOT / storage.get("editions", "data/editions")
    edition_dir.mkdir(parents=True, exist_ok=True)
    epub_path = edition_dir / f"{branch_id}-0neNews.epub"

    generator = EpubGenerator(timezone=settings.get("timezone", "Asia/Ho_Chi_Minh"))
    generator.generate(
        article_pool=pool_root,
        output_path=epub_path,
        sources=edition_sources,
        title=settings.get("edition", {}).get("title", "YOUR NEWS"),
        edition_time=settings.get("edition", {}).get("time", "07:00"),
        article_ids=selected_ids,
    )
    validate_epub(epub_path)
    print(
        f"{branch_id}: EPUB validated, articles={len(selected)}, "
        f"bytes={epub_path.stat().st_size}"
    )

    if upload:
        branches = settings.get("_branches", [])
        branch = next((b for b in branches if b.get("id") == branch_id), {})
        folder_id = branch.get("root_folder_id")
        if not folder_id:
            raise RuntimeError(
                f"Cannot upload {branch_id}: branch root_folder_id is missing."
            )
        result = upload_epub(
            epub_path,
            folder_id=folder_id,
            filename=settings.get("drive_upload", {}).get("filename", "0neNews.epub"),
        )
        print(
            f"{branch_id}: Drive upload complete "
            f"(file_id={result.get('file_id', 'unknown')}, "
            f"operation={result.get('operation', 'unknown')})"
        )
    else:
        print(f"{branch_id}: Drive upload skipped by configuration")

    return epub_path


def run(mode: str | None = None, branch_id: str | None = None) -> None:
    settings = load_settings()
    mode = (mode or os.getenv("TANGTHU_CRAWL_MODE", "daily")).strip().lower()
    branch_id = (branch_id or os.getenv("TANGTHU_BRANCH_ID") or "").strip() or None

    if mode not in {"daily", "on-demand"}:
        raise ValueError("TANGTHU_CRAWL_MODE must be 'daily' or 'on-demand'.")
    if mode == "on-demand" and not branch_id:
        raise ValueError("TANGTHU_BRANCH_ID is required for on-demand mode.")

    payload = _fetch_news_config(settings)
    all_active = _active_subscriptions(payload)
    subscriptions = (
        _active_subscriptions(payload, branch_id)
        if mode == "on-demand"
        else all_active
    )

    if mode == "on-demand" and not subscriptions:
        print(f"{branch_id}: no active subscriptions; no crawl/build/upload")
        return

    _edition_limits(all_active if mode == "daily" else subscriptions)

    resolved_sources, all_source_map = _resolve_sources(
        payload["sources"], SourceRegistry().list_sources()
    )
    selected_subscriptions = all_active if mode == "daily" else subscriptions
    used_source_ids = {s["source_id"] for s in selected_subscriptions}
    relevant_sources = [
        source for source in resolved_sources if source["id"] in used_source_ids
    ]
    source_map = {source["id"]: source for source in relevant_sources}

    storage = settings.get("storage", {})
    cache = ArticleCache(ROOT / storage.get("article_cache", "data/article_cache"))
    cache.cleanup_expired()

    planner = CrawlPlanner()
    now = datetime.now(timezone.utc)
    if mode == "daily":
        plan = planner.plan_daily(all_active, cache, now=now)
        decisions = plan.decisions
        branches_to_build = sorted({s["branch_id"] for s in all_active})
    else:
        plan = planner.plan_on_demand(branch_id, subscriptions, cache, now=now)
        decisions = plan.decisions
        branches_to_build = [branch_id]

    article_pool = ArticlePool(
        ROOT / storage.get("article_pool", "data/article_pool")
    )
    _discover_and_crawl(source_map, decisions, settings, article_pool, cache)
    cache.cleanup_expired()

    settings["_branches"] = payload["branches"]
    for target_branch in branches_to_build:
        branch_subs = [
            sub for sub in selected_subscriptions
            if sub["branch_id"] == target_branch
        ]
        _write_edition(
            target_branch,
            branch_subs,
            cache,
            source_map,
            settings,
            upload=os.getenv("TANGTHU_UPLOAD_ENABLED", "false").strip().lower() == "true",
        )


if __name__ == "__main__":
    run()
