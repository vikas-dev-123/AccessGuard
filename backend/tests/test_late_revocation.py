import pytest

from app.checks import RiskRating
from app.checks.late_revocation import check_late_revocation
from tests.helpers import account, build_context, employee


def _ctx(disabled_on, termination_date="2026-06-01", **config):
    return build_context(
        [employee("E1", status="Terminated", termination_date=termination_date)],
        {"loan_system": [account("L1", "E1", "Loan Approver", account_status="Disabled",
                                 status_last_updated=disabled_on)]},
        **config,
    )


def test_flags_account_disabled_well_after_termination():
    findings = check_late_revocation(_ctx("2026-06-11"))

    assert len(findings) == 1
    assert findings[0].risk_rating == RiskRating.MEDIUM
    assert "10 days later" in findings[0].details


@pytest.mark.parametrize("disabled_on", ["2026-06-01", "2026-06-02"])
def test_within_one_day_is_not_late(disabled_on):
    assert check_late_revocation(_ctx(disabled_on)) == []


def test_two_days_is_late():
    assert len(check_late_revocation(_ctx("2026-06-03"))) == 1


def test_grace_period_is_configurable():
    assert check_late_revocation(_ctx("2026-06-04", late_revocation_grace_days=5)) == []


def test_ignores_still_active_accounts():
    ctx = build_context(
        [employee("E1", status="Terminated", termination_date="2026-06-01")],
        {"loan_system": [account("L1", "E1", "Loan Approver", status_last_updated="2026-08-01")]},
    )
    assert check_late_revocation(ctx) == []


def test_ignores_active_employees():
    ctx = build_context(
        [employee("E1")],
        {"loan_system": [account("L1", "E1", "Loan Approver", account_status="Disabled",
                                 status_last_updated="2026-08-01")]},
    )
    assert check_late_revocation(ctx) == []
