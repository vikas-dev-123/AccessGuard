from collections import defaultdict

from app.checks.base import Finding, ReviewContext, RiskRating
from app.checks.registry import register_check

NAME = "Segregation of Duties conflicts"


@register_check(
    code="sod_conflicts",
    name=NAME,
    criteria="No employee may hold a combination of roles that the bank's SoD rule set defines as "
             "conflicting, whether in one system or across systems.",
    impact="One person can start and complete a sensitive transaction, such as creating and approving "
           "a loan or approving and disbursing it, with no independent check. This enables fraud that goes undetected.",
    recommendation="Remove one of the conflicting roles. If staffing makes that impossible, document a "
                   "compensating control, such as independent review of the user's transactions, "
                   "and have the risk owner approve it.",
)
def check_sod_conflicts(ctx: ReviewContext) -> list[Finding]:
    accounts = ctx.all_accounts_with_hr()
    if accounts.empty:
        return []
    accounts = accounts[accounts["is_active"] & accounts["employee_id"].notna()]

    findings = []
    for employee_id, group in accounts.groupby("employee_id", sort=True):
        held: dict[tuple[str, str], list[str]] = defaultdict(list)
        for row in group.itertuples(index=False):
            held[(row.system, row.role)].append(row.username)
        employee_name = group["name"].iloc[0] if group["name"].notna().any() else employee_id

        for rule in ctx.config.sod_rules:
            keys = [(r["system"], r["role"]) for r in rule["conflicting_roles"]]
            if not all(key in held for key in keys):
                continue
            systems = sorted({system for system, _ in keys})
            usernames = sorted({u for key in keys for u in held[key]})
            roles_desc = " and ".join(
                f"'{role}' ({system}: {', '.join(held[(system, role)])})" for system, role in keys
            )
            findings.append(Finding(
                check_name=NAME,
                system=" + ".join(systems),
                employee_id=employee_id,
                username=", ".join(usernames),
                details=f"[{rule['rule_id']}] {employee_name} holds {roles_desc}. {rule.get('description', '')}".strip(),
                risk_rating=RiskRating.HIGH,
            ))
    return findings
