from datetime import date

import pandas as pd

from app.checks import ReviewContext
from app.config import ReviewConfig
from app.data_loading import (
    ACCOUNT_REQUIRED_COLUMNS,
    HR_REQUIRED_COLUMNS,
    normalize_accounts,
    normalize_hr,
)

AS_OF = date(2026, 9, 27)


def employee(employee_id, department="Loans", status="Active", termination_date="",
             name=None, designation="Officer", joining_date="2020-01-01"):
    return {
        "employee_id": employee_id,
        "name": name or f"Person {employee_id}",
        "department": department,
        "designation": designation,
        "status": status,
        "joining_date": joining_date,
        "termination_date": termination_date,
    }


def account(user_id, employee_id, role, username=None, account_status="Active",
            created_date="2023-01-01", last_login_date="2026-09-20", status_last_updated="2023-01-01"):
    return {
        "user_id": user_id,
        "employee_id": employee_id or "",
        "username": username or f"user.{user_id.lower()}",
        "role": role,
        "account_status": account_status,
        "created_date": created_date,
        "last_login_date": last_login_date,
        "status_last_updated": status_last_updated,
    }


def build_context(employees, systems, **config_overrides) -> ReviewContext:
    hr = normalize_hr(pd.DataFrame(employees, columns=HR_REQUIRED_COLUMNS))
    normalized = {
        name: normalize_accounts(pd.DataFrame(rows, columns=ACCOUNT_REQUIRED_COLUMNS))
        for name, rows in systems.items()
    }
    config_overrides.setdefault("as_of_date", AS_OF)
    return ReviewContext(hr, normalized, ReviewConfig(**config_overrides))
