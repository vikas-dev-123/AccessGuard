from app.checks.base import Finding, ReviewContext, RiskRating, fmt_date, opt_str
from app.checks.registry import register_check

NAME = "Terminated users with active access"


@register_check(
    code="terminated_active_access",
    name=NAME,
    condition='accounts belonging to employees marked Terminated in the HR master were still Active.',
    criteria="Access to banking systems must be revoked when employment ends. "
             "Terminated employees must not hold active accounts.",
    impact="A former employee, or anyone holding their credentials, can still log in and "
           "process transactions or read customer data, with no one accountable for the activity.",
    recommendation="Disable these accounts immediately. Review all activity after each termination "
                   "date for unauthorised transactions, and automate the HR-to-IT leaver "
                   "notification so revocation starts on the termination date.",
)
def check_terminated_active_access(ctx: ReviewContext) -> list[Finding]:
    findings = []
    for system, accounts in ctx.accounts_with_hr().items():
        hits = accounts[(accounts["status"] == "Terminated") & accounts["is_active"]]
        for row in hits.itertuples(index=False):
            details = (
                f"{row.name} ({row.department}) was terminated on {fmt_date(row.termination_date)}, "
                f"but account '{row.username}' with role '{row.role}' is still Active."
            )
            if row.last_login_date is not None and row.termination_date is not None \
                    and row.last_login_date > row.termination_date:
                details += f" Last login on {fmt_date(row.last_login_date)} was after the termination date."
            findings.append(Finding(
                check_name=NAME,
                system=system,
                employee_id=opt_str(row.employee_id),
                username=row.username,
                details=details,
                risk_rating=RiskRating.HIGH,
            ))
    return findings
