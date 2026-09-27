from app.checks import RiskRating
from app.checks.sod_conflicts import check_sod_conflicts
from tests.helpers import account, build_context, employee

CROSS_SYSTEM_RULE = {
    "rule_id": "SOD-X",
    "description": "Opening accounts and approving loans across systems.",
    "conflicting_roles": [
        {"system": "core_banking", "role": "Account Opener"},
        {"system": "loan_system", "role": "Loan Approver"},
    ],
}


def test_flags_conflict_within_one_system():
    ctx = build_context(
        [employee("E1")],
        {"loan_system": [account("L1", "E1", "Loan Creator", username="a.creator"),
                         account("L2", "E1", "Loan Approver", username="a.approver")]},
    )
    findings = check_sod_conflicts(ctx)

    assert len(findings) == 1
    f = findings[0]
    assert f.risk_rating == RiskRating.HIGH
    assert f.system == "loan_system"
    assert f.employee_id == "E1"
    assert f.username == "a.approver, a.creator"
    assert "SOD-01" in f.details


def test_flags_conflict_across_systems():
    ctx = build_context(
        [employee("E1")],
        {"core_banking": [account("C1", "E1", "Account Opener", username="cb.user")],
         "loan_system": [account("L1", "E1", "Loan Approver", username="ln.user")]},
        sod_rules=[CROSS_SYSTEM_RULE],
    )
    findings = check_sod_conflicts(ctx)

    assert len(findings) == 1
    assert findings[0].system == "core_banking + loan_system"
    assert findings[0].username == "cb.user, ln.user"


def test_roles_split_between_employees_is_not_a_conflict():
    ctx = build_context(
        [employee("E1"), employee("E2")],
        {"loan_system": [account("L1", "E1", "Loan Creator"), account("L2", "E2", "Loan Approver")]},
    )
    assert check_sod_conflicts(ctx) == []


def test_disabled_account_does_not_create_conflict():
    ctx = build_context(
        [employee("E1")],
        {"loan_system": [account("L1", "E1", "Loan Creator"),
                         account("L2", "E1", "Loan Approver", account_status="Disabled")]},
    )
    assert check_sod_conflicts(ctx) == []


def test_one_finding_per_rule_violated():
    ctx = build_context(
        [employee("E1")],
        {"loan_system": [account("L1", "E1", "Loan Creator"),
                         account("L2", "E1", "Loan Approver"),
                         account("L3", "E1", "Disbursement Officer")]},
    )
    assert sorted(f.details[:8] for f in check_sod_conflicts(ctx)) == ["[SOD-01]", "[SOD-02]"]


def test_same_role_names_in_different_systems_do_not_match():
    ctx = build_context(
        [employee("E1")],
        {"loan_system": [account("L1", "E1", "Developer")],
         "database": [account("D1", "E1", "DBA")]},
    )
    assert check_sod_conflicts(ctx) == []
