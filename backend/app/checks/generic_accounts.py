import re

from app.checks.base import Finding, ReviewContext, RiskRating, opt_str
from app.checks.registry import register_check

NAME = "Generic/shared accounts"


@register_check(
    code="generic_shared_accounts",
    name=NAME,
    condition='active accounts use generic, shared, test or temporary usernames that are not tied to one individual.',
    criteria="Each account must belong to one named individual. Generic, shared, test, and temporary "
             "accounts are not allowed in production without a documented exception.",
    impact="When a login is shared, no action can be traced to one person, so fraud or errors on "
           "these accounts cannot be attributed and accountability controls stop working.",
    recommendation="Replace shared accounts with named individual accounts. Where a generic account "
                   "has to exist, record its business reason, assign a named custodian, restrict it, "
                   "and store its credentials in a privileged access vault.",
)
def check_generic_shared_accounts(ctx: ReviewContext) -> list[Finding]:
    patterns = [re.compile(p, re.IGNORECASE) for p in ctx.config.generic_username_patterns]
    findings = []
    for system, accounts in ctx.accounts_with_hr().items():
        for row in accounts[accounts["is_active"]].itertuples(index=False):
            username = row.username or ""
            matched = next((p.pattern for p in patterns if p.search(username)), None)
            if matched is None:
                continue
            details = f"Username '{username}' ({row.role}) matches generic/shared pattern '{matched}'."
            if row.in_hr:
                details += f" Named custodian in HR: {row.name} ({row.department})."
            findings.append(Finding(
                check_name=NAME,
                system=system,
                employee_id=opt_str(row.employee_id),
                username=username,
                details=details,
                risk_rating=RiskRating.MEDIUM,
            ))
    return findings
