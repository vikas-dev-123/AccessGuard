from app.checks import RiskRating
from app.checks.terminated_access import check_terminated_active_access
from tests.helpers import account, build_context, employee


def test_flags_terminated_employee_with_active_account():
    ctx = build_context(
        [employee("E1", status="Terminated", termination_date="2026-06-01"), employee("E2")],
        {"loan_system": [account("L1", "E1", "Loan Creator", username="bob.t"),
                         account("L2", "E2", "Loan Creator")]},
    )
    findings = check_terminated_active_access(ctx)

    assert len(findings) == 1
    f = findings[0]
    assert (f.system, f.employee_id, f.username) == ("loan_system", "E1", "bob.t")
    assert f.risk_rating == RiskRating.HIGH
    assert "2026-06-01" in f.details


def test_ignores_disabled_accounts_of_terminated_employees():
    ctx = build_context(
        [employee("E1", status="Terminated", termination_date="2026-06-01")],
        {"loan_system": [account("L1", "E1", "Loan Creator", account_status="Disabled")]},
    )
    assert check_terminated_active_access(ctx) == []


def test_notes_login_after_termination():
    ctx = build_context(
        [employee("E1", status="Terminated", termination_date="2026-06-01")],
        {"core_banking": [account("C1", "E1", "Teller", last_login_date="2026-07-15")]},
    )
    assert "after the termination date" in check_terminated_active_access(ctx)[0].details


def test_status_matching_is_case_insensitive():
    ctx = build_context(
        [employee("E1", status=" terminated ", termination_date="2026-06-01")],
        {"core_banking": [account("C1", "E1", "Teller", account_status="ACTIVE")]},
    )
    assert len(check_terminated_active_access(ctx)) == 1


def test_reports_one_finding_per_system():
    ctx = build_context(
        [employee("E1", status="Terminated", termination_date="2026-06-01")],
        {"core_banking": [account("C1", "E1", "Teller")],
         "database": [account("D1", "E1", "Read Only")]},
    )
    assert sorted(f.system for f in check_terminated_active_access(ctx)) == ["core_banking", "database"]
