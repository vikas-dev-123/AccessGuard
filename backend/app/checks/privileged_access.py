from app.checks.base import Finding, ReviewContext, RiskRating, opt_str
from app.checks.registry import register_check

NAME = "Privileged access"


@register_check(
    code="privileged_access",
    name=NAME,
    condition='active privileged (Admin or DBA) accounts were identified. Accounts held outside the IT department, or with no HR record, are rated High; accounts held by IT staff are listed as Informational for recertification.',
    criteria="Privileged roles (Admin, DBA) must be limited to IT staff whose job requires them, "
             "and must be reviewed regularly.",
    impact="A privileged user can change configuration, security settings, and data directly, which "
           "bypasses application controls. Business users holding these roles can hide unauthorised changes.",
    recommendation="Remove privileged roles from business users, or record a time-bound approved "
                   "exception. Log and monitor privileged activity, and recertify privileged access every quarter.",
)
def check_privileged_access(ctx: ReviewContext) -> list[Finding]:
    privileged_roles = ctx.config.privileged_roles
    it_department = ctx.config.it_department
    findings = []
    for system, accounts in ctx.accounts_with_hr().items():
        hits = accounts[accounts["is_active"] & accounts["role"].isin(privileged_roles)]
        for row in hits.itertuples(index=False):
            if not row.in_hr:
                risk = RiskRating.HIGH
                details = f"Privileged role '{row.role}' on account '{row.username}' has no HR record for its holder."
            elif row.department == it_department:
                risk = RiskRating.INFORMATIONAL
                details = (
                    f"Privileged role '{row.role}' held by {row.name} ({row.designation}, {row.department}). "
                    "The holder is in IT; include this account in the privileged access recertification."
                )
            else:
                risk = RiskRating.HIGH
                details = (
                    f"Privileged role '{row.role}' held by {row.name} ({row.designation}), who is in "
                    f"the {row.department} department, outside {it_department}."
                )
            findings.append(Finding(
                check_name=NAME,
                system=system,
                employee_id=opt_str(row.employee_id),
                username=row.username,
                details=details,
                risk_rating=risk,
            ))
    return findings
