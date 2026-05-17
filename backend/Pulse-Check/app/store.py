from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class MonitorStatus(str, Enum):
    ACTIVE = "active"
    DOWN = "down"
    PAUSED = "paused"


@dataclass
class Monitor:
    id: str
    timeout: int                        # seconds
    alert_email: str
    status: MonitorStatus = MonitorStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_ping_at: Optional[datetime] = None
    deadline: Optional[datetime] = None  # when timer expires
    alert_fired: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timeout": self.timeout,
            "alert_email": self.alert_email,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "last_ping_at": self.last_ping_at.isoformat() if self.last_ping_at else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "alert_fired": self.alert_fired,
        }


# In-memory store — keyed by monitor id
_store: Dict[str, Monitor] = {}


def get_store() -> Dict[str, Monitor]:
    return _store
