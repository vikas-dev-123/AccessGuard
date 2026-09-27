from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checks import CheckDefinition, RiskRating, get_checks
from app.models import Dataset, FindingRecord, Review
from app.settings import settings

RISK_ORDER = [r.value for r in RiskRating]

SYSTEM_LABELS = {
    "core_banking": "Core Banking",
    "loan_system": "Loan System",
    "database": "Database",
}


def system_label(system: str) -> str:
    return " + ".join(SYSTEM_LABELS.get(s, s.replace("_", " ").title()) for s in system.split(" + "))


def fmt_date(value) -> str:
    return value.strftime("%d %b %Y")


@dataclass
class CheckSection:
    number: int
    check: CheckDefinition
    findings: list[FindingRecord]

    @property
    def by_risk(self) -> dict[str, int]:
        counts = Counter(f.risk_rating for f in self.findings)
        return {r: counts[r] for r in RISK_ORDER if counts[r]}

    @property
    def by_system(self) -> list[tuple[str, int]]:
        return Counter(f.system for f in self.findings).most_common()

    @property
    def rating(self) -> str | None:
        return next(iter(self.by_risk), None)

    def condition_text(self, as_of: str) -> str:
        n = len(self.findings)
        if n == 0:
            return f"No exceptions were identified for this check as of {as_of}."
        systems = ", ".join(f"{system_label(s)} ({c})" for s, c in self.by_system)
        risks = ", ".join(f"{c} {r}" for r, c in self.by_risk.items())
        return (f"As of {as_of}, {n} {self.check.condition} "
                f"Affected systems: {systems}. Risk rating: {risks}.")


@dataclass
class ReportData:
    organization: str
    review: Review
    dataset: Dataset
    findings: list[FindingRecord]
    sections: list[CheckSection]
    generated_at: datetime

    @property
    def title(self) -> str:
        return f"User Access Review — {self.organization}"

    @property
    def as_of(self) -> str:
        return fmt_date(self.review.as_of_date)

    @property
    def systems(self) -> list[str]:
        return [system_label(s) for s in self.review.systems]

    @property
    def total_accounts(self) -> int:
        return sum(self.dataset.account_counts.get(s, 0) for s in self.review.systems)

    @property
    def by_risk(self) -> dict[str, int]:
        counts = Counter(f.risk_rating for f in self.findings)
        return {r: counts[r] for r in RISK_ORDER}

    def filename(self, extension: str) -> str:
        org = "".join(c if c.isalnum() else "_" for c in self.organization).strip("_")
        return f"AccessGuard_UAR_{org}_{self.review.as_of_date.isoformat()}_review{self.review.id}.{extension}"


def build_report_data(db: Session, review: Review) -> ReportData:
    findings = list(db.scalars(
        select(FindingRecord).where(FindingRecord.review_id == review.id).order_by(FindingRecord.id)
    ))
    by_check: dict[str, list[FindingRecord]] = {}
    for f in findings:
        by_check.setdefault(f.check_code, []).append(f)
    sections = [
        CheckSection(number=i, check=check, findings=by_check.get(check.code, []))
        for i, check in enumerate(get_checks(), start=1)
    ]
    return ReportData(
        organization=settings.organization_name,
        review=review,
        dataset=db.get(Dataset, review.dataset_id),
        findings=findings,
        sections=sections,
        generated_at=datetime.now(timezone.utc),
    )
