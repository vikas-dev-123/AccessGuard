import pytest

from app.checks import RiskRating
from app.checks.dormant_accounts import check_dormant_accounts
from tests.helpers import account, build_context, employee


def _ctx(last_login_date, created_date="2023-01-01", account_status="Active", **config):
    return build_context(
        [employee("E1")],
        {"database": [account("D1", "E1", "Read Only", last_login_date=last_login_date,
                              created_date=created_date, account_status=account_status)]},
        **config,
    )


@pytest.mark.parametrize("last_login, expected", [
    ("2026-06-29", 1),   # exactly 90 days before 2026-09-27
    ("2026-06-30", 0),   # 89 days
    ("2025-08-01", 1),
])
def test_threshold_boundary(last_login, expected):
    assert len(check_dormant_accounts(_ctx(last_login))) == expected


def test_finding_details_and_risk():
    finding = check_dormant_accounts(_ctx("2026-06-29"))[0]
    assert finding.risk_rating == RiskRating.LOW
    assert "90 days" in finding.details


def test_never_logged_in_old_account_is_dormant():
    findings = check_dormant_accounts(_ctx("", created_date="2026-01-01"))
    assert len(findings) == 1
    assert "never logged in" in findings[0].details


def test_never_logged_in_new_account_is_not_dormant():
    assert check_dormant_accounts(_ctx("", created_date="2026-09-17")) == []


def test_ignores_disabled_accounts():
    assert check_dormant_accounts(_ctx("2025-01-01", account_status="Disabled")) == []


def test_threshold_is_configurable():
    assert len(check_dormant_accounts(_ctx("2026-08-20", dormant_days=30))) == 1
