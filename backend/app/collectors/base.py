from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from typing import Any


class CollectorStatus(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    BLOCKED = "blocked"


@dataclass
class CollectResult:
    status: CollectorStatus
    records_count: int = 0
    errors: list[str] = field(default_factory=list)
    raw_response: Any = None
    collected_at: datetime = field(default_factory=datetime.utcnow)


class BaseCollector(ABC):
    source_name: str = "base"
    update_frequency: timedelta = timedelta(hours=6)

    @abstractmethod
    async def collect(self, target_date: datetime | None = None) -> CollectResult:
        ...

    def validate(self, data: Any) -> bool:
        return True

    def needs_update(self, db_session, last_collection_hours: int = 6) -> bool:
        from app.models import CollectionLog

        last_log = (
            db_session.query(CollectionLog)
            .filter(
                CollectionLog.collector_name == self.source_name,
                CollectionLog.status.in_(["success", "partial"]),
            )
            .order_by(CollectionLog.completed_at.desc())
            .first()
        )
        if not last_log or not last_log.completed_at:
            return True
        elapsed = datetime.utcnow() - last_log.completed_at
        return elapsed > timedelta(hours=last_collection_hours)
