from __future__ import annotations

from collections import defaultdict
from datetime import date

import pandas as pd
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.checks import Finding, ReviewContext, RiskRating, get_checks
from app.config import ReviewConfig
from app.data_loading import ACCOUNT_REQUIRED_COLUMNS, HR_REQUIRED_COLUMNS, normalize_accounts, normalize_hr
from app.models import Dataset, FindingRecord, HREmployee, Review, SystemAccount
from app.review import run_all_checks, summarize


def load_dataset_frames(db: Session, dataset: Dataset) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    employees = db.scalars(select(HREmployee).where(HREmployee.dataset_id == dataset.id)).all()
    hr = normalize_hr(pd.DataFrame(
        [{c: getattr(e, c) for c in HR_REQUIRED_COLUMNS} for e in employees], columns=HR_REQUIRED_COLUMNS))

    rows_by_system: dict[str, list[dict]] = defaultdict(list)
    for a in db.scalars(select(SystemAccount).where(SystemAccount.dataset_id == dataset.id)):
        rows_by_system[a.system].append({c: getattr(a, c) for c in ACCOUNT_REQUIRED_COLUMNS})
    systems = {
        s: normalize_accounts(pd.DataFrame(rows_by_system[s], columns=ACCOUNT_REQUIRED_COLUMNS), s)
        for s in dataset.systems
    }
    return hr, systems


def run_review(db: Session, dataset: Dataset, as_of_date: date, run_by: str) -> Review:
    hr, systems = load_dataset_frames(db, dataset)
    findings = run_all_checks(ReviewContext(hr, systems, ReviewConfig(as_of_date=as_of_date)))
    code_by_name = {c.name: c.code for c in get_checks()}

    review = Review(dataset_id=dataset.id, run_by=run_by, as_of_date=as_of_date,
                    systems=list(dataset.systems), total_findings=len(findings))
    review.findings = [
        FindingRecord(
            finding_id=f.finding_id, check_code=code_by_name[f.check_name], check_name=f.check_name,
            system=f.system, employee_id=f.employee_id, username=f.username, details=f.details,
            risk_rating=f.risk_rating.value, detected_at=f.detected_at,
        )
        for f in findings
    ]
    db.add(review)
    db.commit()
    return review


def query_findings(db: Session, review_id: int, *, system: str | None = None, check: str | None = None,
                   risk_rating: str | None = None, search: str | None = None,
                   limit: int = 500, offset: int = 0) -> tuple[int, list[FindingRecord]]:
    stmt = select(FindingRecord).where(FindingRecord.review_id == review_id)
    if system:
        # Cross-system SoD findings are stored as "core_banking + loan_system".
        stmt = stmt.where(FindingRecord.system.contains(system))
    if check:
        stmt = stmt.where(FindingRecord.check_code == check)
    if risk_rating:
        stmt = stmt.where(FindingRecord.risk_rating == risk_rating)
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(or_(
            func.lower(FindingRecord.username).like(like),
            func.lower(FindingRecord.employee_id).like(like),
            func.lower(FindingRecord.details).like(like),
            func.lower(FindingRecord.finding_id).like(like),
        ))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(FindingRecord.id).offset(offset).limit(limit)).all()
    return total, list(items)


def to_finding(record: FindingRecord) -> Finding:
    return Finding(
        check_name=record.check_name, system=record.system, employee_id=record.employee_id,
        username=record.username, details=record.details, risk_rating=RiskRating(record.risk_rating),
        finding_id=record.finding_id, detected_at=record.detected_at,
    )


def review_summary(db: Session, review: Review) -> dict:
    records = db.scalars(select(FindingRecord).where(FindingRecord.review_id == review.id)).all()
    return summarize([to_finding(r) for r in records])
