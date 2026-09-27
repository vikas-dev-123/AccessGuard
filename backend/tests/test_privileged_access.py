from app.checks import RiskRating
from app.checks.privileged_access import check_privileged_access
from tests.helpers import account, build_context, employee


def _findings_by_user(ctx):
    return {f.username: f for f in check_privileged_access(ctx)}


def test_rates_by_department():
    ctx = build_context(
        [employee("E1", department="IT"), employee("E2", department="Finance")],
        {"core_banking": [account("C1", "E1", "Admin", username="it.admin")],
         "database": [account("D1", "E2", "DBA", username="fin.dba")]},
    )
    findings = _findings_by_user(ctx)

    assert findings["it.admin"].risk_rating == RiskRating.INFORMATIONAL
    assert findings["fin.dba"].risk_rating == RiskRating.HIGH
    assert "Finance" in findings["fin.dba"].details


def test_privileged_account_without_hr_record_is_high():
    ctx = build_context([], {"core_banking": [account("C1", None, "Admin", username="root.x")]})
    finding = _findings_by_user(ctx)["root.x"]

    assert finding.risk_rating == RiskRating.HIGH
    assert "no HR record" in finding.details


def test_ignores_non_privileged_and_disabled_accounts():
    ctx = build_context(
        [employee("E1", department="Finance")],
        {"core_banking": [account("C1", "E1", "Teller"),
                          account("C2", "E1", "Admin", account_status="Disabled")]},
    )
    assert check_privileged_access(ctx) == []


def test_privileged_roles_are_configurable():
    ctx = build_context(
        [employee("E1", department="Loans")],
        {"loan_system": [account("L1", "E1", "Loan Approver")]},
        privileged_roles=frozenset({"Loan Approver"}),
    )
    assert len(check_privileged_access(ctx)) == 1
