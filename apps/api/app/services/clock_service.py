"""
Simulated Clock Service for Pakka.
Enables virtual time manipulation, step advances, and schedule evaluation
for automated money collections and promise due-date transitions.
"""

from __future__ import annotations

import datetime as dt
from datetime import datetime, timedelta, timezone
from typing import Any

# IST is UTC+05:30
IST = timezone(timedelta(hours=5, minutes=30))

# Baseline simulated time: Wednesday 4 Nov 2026 10:00:00 AM IST
DEFAULT_BASE_TIME = datetime(2026, 11, 4, 10, 0, 0, tzinfo=IST)


class SimulatedClock:
    """Singleton virtual clock service with step advance and bound checks."""

    def __init__(self, base_time: datetime | None = None) -> None:
        self.base_time: datetime = base_time or DEFAULT_BASE_TIME
        self.offset: timedelta = timedelta(0)
        self.speed: float = 1.0
        self.is_paused: bool = False

    def now(self) -> datetime:
        """Return current simulated time in IST."""
        return self.base_time + self.offset

    def now_iso(self) -> str:
        """Return ISO formatted string of current simulated time."""
        return self.now().isoformat()

    def advance(self, hours: float = 0.0, days: float = 0.0) -> datetime:
        """Advance the simulated clock forward."""
        delta = timedelta(hours=hours, days=days)
        self.offset += delta
        return self.now()

    def reset(self) -> datetime:
        """Reset the clock back to initial baseline."""
        self.offset = timedelta(0)
        return self.now()

    def is_within_outbound_hours(
        self,
        start_time_str: str = "09:00",
        end_time_str: str = "20:00",
    ) -> bool:
        """Check if current simulated time is within owner outbound calling window."""
        current_time = self.now().time()
        start_h, start_m = map(int, start_time_str.split(":"))
        end_h, end_m = map(int, end_time_str.split(":"))
        start = dt.time(start_h, start_m)
        end = dt.time(end_h, end_m)
        return start <= current_time <= end

    def to_dict(self) -> dict[str, Any]:
        """Serialize clock state for API clients."""
        current = self.now()
        return {
            "simulated_time": current.isoformat(),
            "formatted": current.strftime("%A, %d %b %Y, %I:%M %p IST"),
            "date_key": current.strftime("%Y-%m-%d"),
            "offset_hours": round(self.offset.total_seconds() / 3600, 2),
            "speed": self.speed,
            "is_paused": self.is_paused,
            "is_outbound_hours": self.is_within_outbound_hours(),
        }


# Global singleton clock
clock = SimulatedClock()
