from app.checks.base import Finding, ReviewContext, RiskRating, fmt_date, opt_str
from app.checks.registry import register_check

NAME = "Late revocation"


@register_check(
    code="late_revocation",
    name=NAME,
    condition='accounts of terminated employees were disabled more than one day after the termination date.',
    criteria="Accounts of terminated employees must be disabled within 1 day of the termination date.",
    impact="While revocation is delayed, a departed employee keeps access. Transactions or data "
           "access in that window cannot be prevented and are often never investigated.",
    recommendation="Check activity on these accounts between the termination and disable dates. "
                   "Set a revocation SLA with the HR and IT teams and track how often it is breached.",
)
def check_late_revocation(ctx: ReviewContext) -> list[Finding]:
    grace_days = ctx.config.late_revocation_grace_days
    findings = []
    for system, accounts in ctx.accounts_with_hr().items():
        candidates = accounts[
            (accounts["status"] == "Terminated")
            & ~accounts["is_active"]
            & accounts["termination_date"].notna()
            & accounts["status_last_updated"].notna()
        ]
        delay_days = (candidates["status_last_updated"] - candidates["termination_date"]).dt.days
        hits = candidates[delay_days > grace_days]
        for row, delay in zip(hits.itertuples(index=False), delay_days[delay_days > grace_days]):
            findings.append(Finding(
                check_name=NAME,
                system=system,
                employee_id=opt_str(row.employee_id),
                username=row.username,
                details=(
                    f"{row.name} was terminated on {fmt_date(row.termination_date)}, but account "
                    f"'{row.username}' ({row.role}) was only disabled on {fmt_date(row.status_last_updated)}, "
                    f"{delay} days later. The allowed window is {grace_days} day(s)."
                ),
                risk_rating=RiskRating.MEDIUM,
            ))
    return findings
