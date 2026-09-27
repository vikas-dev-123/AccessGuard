from app.checks import RiskRating
from app.checks.orphan_accounts import check_orphan_accounts
from tests.helpers import account, build_context, employee


def test_flags_missing_and_unknown_employee_ids():
    ctx = build_context(
        [employee("E1")],
        {"database": [account("D1", "E1", "Read Only"),
                      account("D2", None, "Developer", username="vendor.x"),
                      account("D3", "E999", "Read Only", username="ghost")]},
    )
    findings = {f.username: f for f in check_orphan_accounts(ctx)}

    assert set(findings) == {"vendor.x", "ghost"}
    assert all(f.risk_rating == RiskRating.HIGH for f in findings.values())
    assert "no employee_id" in findings["vendor.x"].details
    assert "E999" in findings["ghost"].details
    assert findings["vendor.x"].employee_id is None


def test_ignores_disabled_orphans():
    ctx = build_context(
        [employee("E1")],
        {"database": [account("D1", None, "Developer", account_status="Disabled")]},
    )
    assert check_orphan_accounts(ctx) == []


def test_terminated_employee_is_not_an_orphan():
    ctx = build_context(
        [employee("E1", status="Terminated", termination_date="2026-01-01")],
        {"database": [account("D1", "E1", "Developer")]},
    )
    assert check_orphan_accounts(ctx) == []
