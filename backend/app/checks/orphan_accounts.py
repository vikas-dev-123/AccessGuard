from app.checks.base import Finding, ReviewContext, RiskRating, opt_str
from app.checks.registry import register_check

NAME = "Orphan accounts"


@register_check(
    code="orphan_accounts",
    name=NAME,
    condition='active accounts could not be matched to any employee in the HR master.',
    criteria="Every active system account must be traceable to a current employee in the HR master record.",
    impact="An account with no owner cannot be held to account. Orphan accounts are a common route "
           "for fraud, and often belong to contractors, test setups, or leavers missing from HR records.",
    recommendation="Identify an owner for each account and link it to an HR record, or disable it. "
                   "Require a valid employee ID for every new account request.",
)
def check_orphan_accounts(ctx: ReviewContext) -> list[Finding]:
    findings = []
    for system, accounts in ctx.accounts_with_hr().items():
        hits = accounts[accounts["is_active"] & ~accounts["in_hr"]]
        for row in hits.itertuples(index=False):
            employee_id = opt_str(row.employee_id)
            if employee_id is None:
                reason = "has no employee_id recorded"
            else:
                reason = f"is linked to employee_id '{employee_id}', which does not exist in the HR master"
            findings.append(Finding(
                check_name=NAME,
                system=system,
                employee_id=employee_id,
                username=row.username,
                details=f"Active account '{row.username}' ({row.role}) {reason}.",
                risk_rating=RiskRating.HIGH,
            ))
    return findings
