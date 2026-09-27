import pytest

from app.checks import RiskRating
from app.checks.generic_accounts import check_generic_shared_accounts
from tests.helpers import account, build_context, employee


def _ctx(username, account_status="Active", **config):
    return build_context(
        [employee("E1", department="IT")],
        {"core_banking": [account("C1", "E1", "Teller", username=username, account_status=account_status)]},
        **config,
    )


@pytest.mark.parametrize("username", [
    "admin", "admin2", "ADMIN", "backup_admin", "test", "testuser", "temp", "temp_user",
    "teller01", "shared", "shared_acct", "training", "demo",
])
def test_flags_generic_usernames(username):
    findings = check_generic_shared_accounts(_ctx(username))

    assert len(findings) == 1
    assert findings[0].risk_rating == RiskRating.MEDIUM
    assert "Person E1" in findings[0].details


@pytest.mark.parametrize("username", ["john.smith", "temple.jones", "teller.mary", "sharon.test", "admin.kumar"])
def test_ignores_personal_usernames(username):
    assert check_generic_shared_accounts(_ctx(username)) == []


def test_ignores_disabled_generic_accounts():
    assert check_generic_shared_accounts(_ctx("admin", account_status="Disabled")) == []


def test_patterns_are_configurable():
    ctx = _ctx("svc_batch", generic_username_patterns=(r"^svc_",))
    assert len(check_generic_shared_accounts(ctx)) == 1
