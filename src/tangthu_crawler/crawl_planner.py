
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable


def _parse_dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _active_subscriptions(subscriptions: Iterable[dict[str, Any]], branch_id: str | None = None):
    for sub in subscriptions:
        if not sub.get("enabled", True):
            continue
        if branch_id is not None and sub.get("branch_id") != branch_id:
            continue
        yield sub


def _strongest_mode(modes: Iterable[str]) -> str:
    return "images" if any(mode == "images" for mode in modes) else "text"


def _cache_key(article: dict[str, Any]) -> str:
    return str(article.get("canonical_url") or article.get("id") or "")


def _usable_cached(
    cache: Any,
    source_id: str,
    *,
    now: str | datetime,
    edition_mode: str,
) -> list[dict[str, Any]]:
    if hasattr(cache, "valid_articles"):
        return cache.valid_articles(
            source_id,
            now=now,
            edition_mode=edition_mode,
        )

    # Compatibility fallback for a plain iterable/dict cache used by tests
    # or callers that have not switched to ArticleCache yet.
    if isinstance(cache, dict):
        records = cache.get(source_id, [])
    else:
        records = cache

    now_dt = _parse_dt(now)
    result = []
    seen = set()

    for record in records:
        if record.get("source_id") != source_id:
            continue
        key = _cache_key(record)
        if not key or key in seen:
            continue

        expires_at = record.get("expires_at")
        if not expires_at or _parse_dt(expires_at) <= now_dt:
            continue

        if edition_mode == "images":
            images = record.get("images")
            if images is None:
                images = record.get("image")
            if isinstance(images, str):
                if not images.strip():
                    continue
            elif not images:
                continue

        seen.add(key)
        result.append(record)

    return result


@dataclass(frozen=True)
class CrawlDecision:
    source_id: str
    action: str
    target_count: int
    valid_cached_count: int
    missing_count: int
    reason: str
    edition_mode: str = "text"


@dataclass
class BranchPlan:
    branch_id: str
    decisions: list[CrawlDecision] = field(default_factory=list)
    cancelled: bool = False

    @property
    def sources_to_crawl(self) -> list[str]:
        return [d.source_id for d in self.decisions if d.action == "crawl"]

    @property
    def cache_only_sources(self) -> list[str]:
        return [d.source_id for d in self.decisions if d.action == "cache_only"]


@dataclass
class DailyPlan:
    decisions: list[CrawlDecision] = field(default_factory=list)
    branch_plans: list[BranchPlan] = field(default_factory=list)

    @property
    def sources_to_crawl(self) -> list[str]:
        return [d.source_id for d in self.decisions if d.action == "crawl"]

    @property
    def cache_only_sources(self) -> list[str]:
        return [d.source_id for d in self.decisions if d.action == "cache_only"]


class CrawlPlanner:
    def plan_on_demand(
        self,
        branch_id: str,
        subscriptions: Iterable[dict[str, Any]],
        cache: Any,
        *,
        now: str | datetime | None = None,
    ) -> BranchPlan:
        now = now or datetime.now(timezone.utc)
        active = list(_active_subscriptions(subscriptions, branch_id))

        if not active:
            return BranchPlan(branch_id=branch_id, cancelled=True)

        grouped: dict[str, list[dict[str, Any]]] = {}
        for sub in active:
            grouped.setdefault(sub["source_id"], []).append(sub)

        decisions = []
        for source_id, subs in grouped.items():
            target_count = max(int(s.get("article_count", 0)) for s in subs)
            mode = _strongest_mode(s.get("edition_mode", "text") for s in subs)
            cached = _usable_cached(
                cache,
                source_id,
                now=now,
                edition_mode=mode,
            )
            valid_count = len(cached)

            if valid_count >= target_count:
                decisions.append(
                    CrawlDecision(
                        source_id=source_id,
                        action="cache_only",
                        target_count=target_count,
                        valid_cached_count=valid_count,
                        missing_count=0,
                        reason="valid cache is sufficient",
                        edition_mode=mode,
                    )
                )
            else:
                decisions.append(
                    CrawlDecision(
                        source_id=source_id,
                        action="crawl",
                        target_count=target_count,
                        valid_cached_count=valid_count,
                        missing_count=target_count - valid_count,
                        reason="valid cache is insufficient",
                        edition_mode=mode,
                    )
                )

        return BranchPlan(branch_id=branch_id, decisions=decisions)

    def plan_daily(
        self,
        subscriptions: Iterable[dict[str, Any]],
        cache: Any,
        *,
        now: str | datetime | None = None,
    ) -> DailyPlan:
        now = now or datetime.now(timezone.utc)
        active = list(_active_subscriptions(subscriptions))

        grouped: dict[str, list[dict[str, Any]]] = {}
        for sub in active:
            grouped.setdefault(sub["source_id"], []).append(sub)

        decisions = []
        for source_id, subs in grouped.items():
            target_count = max(int(s.get("article_count", 0)) for s in subs)
            mode = _strongest_mode(s.get("edition_mode", "text") for s in subs)
            cached = _usable_cached(
                cache,
                source_id,
                now=now,
                edition_mode=mode,
            )
            valid_count = len(cached)

            # Daily mode crawls every subscribed source once. target_count
            # expresses the largest requirement that this crawl must satisfy.
            decisions.append(
                CrawlDecision(
                    source_id=source_id,
                    action="crawl",
                    target_count=target_count,
                    valid_cached_count=valid_count,
                    missing_count=max(0, target_count - valid_count),
                    reason="daily refresh for subscribed source",
                    edition_mode=mode,
                )
            )

        branch_plans = [
            self.plan_on_demand(
                branch_id,
                active,
                cache,
                now=now,
            )
            for branch_id in sorted({s["branch_id"] for s in active})
        ]

        return DailyPlan(
            decisions=decisions,
            branch_plans=branch_plans,
        )


def plan_to_dict(plan: CrawlDecision | BranchPlan | DailyPlan) -> dict[str, Any]:
    if isinstance(plan, CrawlDecision):
        return {
            "source_id": plan.source_id,
            "action": plan.action,
            "target_count": plan.target_count,
            "valid_cached_count": plan.valid_cached_count,
            "missing_count": plan.missing_count,
            "reason": plan.reason,
            "edition_mode": plan.edition_mode,
        }

    if isinstance(plan, BranchPlan):
        return {
            "branch_id": plan.branch_id,
            "cancelled": plan.cancelled,
            "decisions": [plan_to_dict(d) for d in plan.decisions],
        }

    return {
        "decisions": [plan_to_dict(d) for d in plan.decisions],
        "branch_plans": [plan_to_dict(p) for p in plan.branch_plans],
    }
