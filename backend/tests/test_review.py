import json

import pandas as pd
import pytest

from app.checks import get_checks
from app.config import load_sod_rules
from app.data_loading import DataValidationError, HR_REQUIRED_COLUMNS, normalize_accounts, normalize_hr
from app.review import run_all_checks, summarize
from tests.helpers import account, build_context, employee

FINDING_KEYS = ["finding_id", "check_name", "system", "employee_id",
                "username", "details", "risk_rating", "detected_at"]


def test_all_seven_checks_registered_in_order():
    assert [c.code for c in get_checks()] == [
        "terminated_active_access", "late_revocation", "orphan_accounts",
        "generic_shared_accounts", "privileged_access", "sod_conflicts", "dormant_accounts",
    ]
    for check in get_checks():
        assert check.criteria and check.impact and check.recommendation


@pytest.fixture
def mixed_context():
    return build_context(
        [employee("E1", status="Terminated", termination_date="2026-06-01"),
         employee("E2", department="Finance")],
        {"core_banking": [account("C1", "E1", "Teller"),
                          account("C2", "E2", "Admin", username="fin.admin"),
                          account("C3", None, "Teller", username="shared")]},
    )


def test_run_all_checks_assigns_ids_and_timestamp(mixed_context):
    findings = run_all_checks(mixed_context)

    assert [f.finding_id for f in findings] == [f"F-{i:04d}" for i in range(1, len(findings) + 1)]
    assert len({f.detected_at for f in findings}) == 1
    assert list(findings[0].to_dict()) == FINDING_KEYS


def test_summary_counts(mixed_context):
    summary = summarize(run_all_checks(mixed_context))

    assert summary["by_check"]["Terminated users with active access"] == 1
    assert summary["by_check"]["Orphan accounts"] == 1
    assert summary["by_check"]["Generic/shared accounts"] == 1
    assert summary["by_check"]["Privileged access"] == 1
    assert summary["by_check"]["Dormant accounts"] == 0
    assert summary["by_risk"] == {"High": 3, "Medium": 1, "Low": 0, "Informational": 0}
    assert summary["total"] == 4
    assert summary["by_system"] == {"core_banking": 4}


def test_missing_columns_are_reported():
    df = pd.DataFrame(columns=["employee_id", "name"])
    with pytest.raises(DataValidationError, match="department"):
        normalize_hr(df)
    with pytest.raises(DataValidationError, match="username"):
        normalize_accounts(pd.DataFrame(columns=["user_id"]), "loan_system_users.csv")


def test_hr_normalization_trims_and_dedupes():
    df = pd.DataFrame([employee(" E1 ", status="active"), employee("E1"), employee("")],
                      columns=HR_REQUIRED_COLUMNS)
    hr = normalize_hr(df)
    assert list(hr["employee_id"]) == ["E1"]
    assert hr["status"].iloc[0] == "Active"


def test_invalid_sod_rules_rejected(tmp_path):
    path = tmp_path / "rules.json"
    path.write_text(json.dumps({"rules": [{"rule_id": "BAD", "conflicting_roles": [{"system": "x", "role": "y"}]}]}))
    with pytest.raises(ValueError, match="Invalid SoD rule"):
        load_sod_rules(path)
