from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

import pandas as pd

from app.config import ReviewConfig

HR_CONTEXT_COLUMNS = [
    "employee_id", "name", "department", "designation",
    "status", "joining_date", "termination_date",
]


class RiskRating(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"


@dataclass
class Finding:
    check_name: str
    system: str
    employee_id: str | None
    username: str
    details: str
    risk_rating: RiskRating
    finding_id: str = ""
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "finding_id": self.finding_id,
            "check_name": self.check_name,
            "system": self.system,
            "employee_id": self.employee_id,
            "username": self.username,
            "details": self.details,
            "risk_rating": self.risk_rating.value,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class ReviewContext:
    hr: pd.DataFrame
    systems: dict[str, pd.DataFrame]
    config: ReviewConfig = field(default_factory=ReviewConfig)

    def __post_init__(self):
        hr_cols = self.hr[HR_CONTEXT_COLUMNS]
        known_ids = set(self.hr["employee_id"])
        self._merged: dict[str, pd.DataFrame] = {}
        for system, accounts in self.systems.items():
            merged = accounts.merge(hr_cols, on="employee_id", how="left")
            merged["in_hr"] = merged["employee_id"].isin(known_ids)
            merged.insert(0, "system", system)
            self._merged[system] = merged

    def accounts_with_hr(self) -> dict[str, pd.DataFrame]:
        """Each system's accounts, left-joined to HR on employee_id."""
        return self._merged

    def all_accounts_with_hr(self) -> pd.DataFrame:
        frames = list(self._merged.values())
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)


def fmt_date(value) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def opt_str(value) -> str | None:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    return value
