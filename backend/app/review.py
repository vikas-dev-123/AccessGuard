from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.checks import CheckDefinition, Finding, ReviewContext, RiskRating, get_checks


def run_all_checks(context: ReviewContext, checks: list[CheckDefinition] | None = None) -> list[Finding]:
    detected_at = datetime.now(timezone.utc)
    findings: list[Finding] = []
    for check in checks if checks is not None else get_checks():
        findings.extend(check.run(context))

    for i, finding in enumerate(findings, start=1):
        finding.finding_id = f"F-{i:04d}"
        finding.detected_at = detected_at
    return findings


def summarize(findings: list[Finding]) -> dict:
    by_risk = Counter(f.risk_rating.value for f in findings)
    by_check = Counter(f.check_name for f in findings)
    by_system = Counter(f.system for f in findings)
    return {
        "total": len(findings),
        "by_risk": {r.value: by_risk.get(r.value, 0) for r in RiskRating},
        "by_check": {c.name: by_check.get(c.name, 0) for c in get_checks()},
        "by_system": dict(sorted(by_system.items())),
    }
