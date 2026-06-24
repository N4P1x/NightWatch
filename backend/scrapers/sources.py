"""
Night-Watch Source Manager
Manages scraping sources: health tracking, scheduling, priority queuing.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import IntEnum
from typing import Any

from backend.scrapers.base import SourceType


class Priority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class ScrapeTarget:
    url: str
    source_id: int
    source_type: SourceType
    name: str = ""
    priority: Priority = Priority.MEDIUM
    interval_minutes: int = 60
    last_scraped: datetime | None = None
    consecutive_failures: int = 0
    reliability_score: float = 1.0
    config: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    @property
    def is_due(self) -> bool:
        if self.last_scraped is None:
            return True
        elapsed = datetime.now(UTC) - self.last_scraped
        return elapsed > timedelta(minutes=self.interval_minutes)

    @property
    def effective_priority(self) -> Priority:
        """Adjust priority based on reliability and failure count."""
        base = self.priority
        if self.consecutive_failures >= 5:
            return Priority.LOW
        if self.reliability_score < 0.3:
            return Priority(min(base + 1, Priority.LOW))
        return base

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "name": self.name,
            "priority": self.effective_priority.name,
            "interval_minutes": self.interval_minutes,
            "last_scraped": self.last_scraped.isoformat() if self.last_scraped else None,
            "consecutive_failures": self.consecutive_failures,
            "reliability_score": round(self.reliability_score, 2),
            "is_due": self.is_due,
            "tags": self.tags,
        }


class SourceManager:
    """
    Manages scraping targets: scheduling, prioritization, health tracking.
    """

    def __init__(self):
        self._targets: dict[int, ScrapeTarget] = {}
        self._history: list[dict[str, Any]] = []
        self._max_history = 1000

    def add_target(self, target: ScrapeTarget):
        self._targets[target.source_id] = target

    def remove_target(self, source_id: int):
        self._targets.pop(source_id, None)

    def get_target(self, source_id: int) -> ScrapeTarget | None:
        return self._targets.get(source_id)

    def get_all_targets(self) -> list[ScrapeTarget]:
        return list(self._targets.values())

    def get_due_targets(self) -> list[ScrapeTarget]:
        """Get all targets that are due for scraping, sorted by priority."""
        due = [t for t in self._targets.values() if t.is_due]
        due.sort(key=lambda t: (t.effective_priority, t.reliability_score))
        return due

    def get_healthy_targets(self) -> list[ScrapeTarget]:
        return [t for t in self._targets.values() if t.reliability_score > 0.3]

    def update_after_success(self, source_id: int, response_time_ms: float):
        target = self._targets.get(source_id)
        if not target:
            return
        target.last_scraped = datetime.now(UTC)
        target.consecutive_failures = 0
        target.reliability_score = min(1.0, target.reliability_score + 0.05)
        self._record_history(source_id, "success", response_time_ms)

    def update_after_failure(self, source_id: int, error: str):
        target = self._targets.get(source_id)
        if not target:
            return
        target.last_scraped = datetime.now(UTC)
        target.consecutive_failures += 1
        target.reliability_score = max(0.0, target.reliability_score - 0.1)
        self._record_history(source_id, "failure", error=error)

    def _record_history(self, source_id: int, status: str, response_time_ms: float = 0, error: str = ""):
        self._history.append({
            "source_id": source_id,
            "status": status,
            "response_time_ms": response_time_ms,
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_stats(self) -> dict[str, Any]:
        targets = list(self._targets.values())
        total = len(targets)
        healthy = sum(1 for t in targets if t.reliability_score > 0.3)
        due = sum(1 for t in targets if t.is_due)
        onion = sum(1 for t in targets if t.source_type == SourceType.TOR_ONION)
        clearnet = total - onion

        return {
            "total_sources": total,
            "healthy": healthy,
            "unhealthy": total - healthy,
            "due_for_scrape": due,
            "onion_sources": onion,
            "clearnet_sources": clearnet,
            "avg_reliability": round(
                sum(t.reliability_score for t in targets) / total, 2
            ) if total > 0 else 0,
        }

    def from_db_sources(self, sources: list[dict[str, Any]]):
        """Load targets from database source records."""
        for src in sources:
            source_type = SourceType.TOR_ONION if src.get("is_onion") else SourceType.CLEARNET
            self.add_target(ScrapeTarget(
                url=src.get("url") or src.get("onion_url", ""),
                source_id=src["id"],
                source_type=source_type,
                name=src.get("name", ""),
                priority=Priority.HIGH if src.get("is_onion") else Priority.MEDIUM,
                interval_minutes=src.get("scrape_interval_minutes", 60),
                reliability_score=src.get("reliability_score", 1.0),
                tags=src.get("tags") or [],
                config=src.get("scraping_config") or {},
            ))
