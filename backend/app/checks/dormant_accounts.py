import pandas as pd

from app.checks.base import Finding, ReviewContext, RiskRating, fmt_date, opt_str
from app.checks.registry import register_check

NAME = "Dormant accounts"


@register_check(
    code="dormant_accounts",
    name=NAME,
    criteria="Active accounts with no login for 90 days or more should be disabled, "
             "or their business need re-confirmed.",
    impact="Unused accounts go unwatched, which makes them easy targets for credential misuse. "
           "They also suggest that access is not being revoked when roles change.",
    recommendation="Disable the dormant accounts after confirming with their owners. Add an automated "
                   "job that disables accounts once they pass the inactivity threshold.",
)
def check_dormant_accounts(ctx: ReviewContext) -> list[Finding]:
    as_of = pd.Timestamp(ctx.config.as_of_date)
    threshold = ctx.config.dormant_days
    findings = []
    for system, accounts in ctx.accounts_with_hr().items():
        active = accounts[accounts["is_active"]]
        for row in active.itertuples(index=False):
            if pd.notna(row.last_login_date):
                idle_days = (as_of - row.last_login_date).days
                if idle_days < threshold:
                    continue
                details = (
                    f"Account '{row.username}' ({row.role}) has not logged in for {idle_days} days "
                    f"(last login {fmt_date(row.last_login_date)}). The threshold is {threshold} days."
                )
            else:
                if pd.isna(row.created_date) or (as_of - row.created_date).days < threshold:
                    continue
                details = (
                    f"Account '{row.username}' ({row.role}) was created on {fmt_date(row.created_date)} "
                    f"and has never logged in. The threshold is {threshold} days."
                )
            findings.append(Finding(
                check_name=NAME,
                system=system,
                employee_id=opt_str(row.employee_id),
                username=row.username,
                details=details,
                risk_rating=RiskRating.LOW,
            ))
    return findings
