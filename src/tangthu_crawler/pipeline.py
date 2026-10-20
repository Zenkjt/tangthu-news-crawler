
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
            local = by_host.get((urlparse(url).hostname or "").lower())

        if local:
            config = dict(local)
            config["html"] = dict(local.get("html", {}))
            config["id"] = source_id
            config["name"] = registered.get("name") or url
            config["url"] = url
            config["status"] = "active"
            config.setdefault("policy", {"mode": "excerpt"})
        else:
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

    return [
        sub
        for sub in payload["subscriptions"]
        if sub.get("enabled", True) is not False
        and sub.get("branch_id") in active_branches
        and sub.get("source_id") in active_sources
        and (not branch_id or sub.get("branch_id") == branch_id)
    ]


def _edition_limits(subscriptions: list[dict]) -> None:
    for branch in sorted({s["branch_id"] for s in subscriptions}):
        branch_subs = [s for s in subscriptions if s["branch_id"] == branch]
        mode = (
            "images"
            if any(s.get("edition_mode") == "images" for s in branch_subs)
            else "text"
        )
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

        if decision.reason == "valid cache is insufficient":
            cached_urls = {
                item.get("canonical_url")
                for item in cache.valid_articles(
                    decision.source_id,
                    edition_mode=decision.edition_mode,
                )
            }
            refs = [
                ref for ref in refs
                if _canonical_url(ref.url) not in cached_urls
            ]

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

    if jobs:
        crawl_sources(jobs, settings, article_pool.root)

    extractor = ArticleExtractor()

    for source_id, refs in refs_by_source.items():
        source = source_map[source_id]
        kept = 0

        for ref in refs:
