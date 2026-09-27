from __future__ import annotations

from pathlib import Path
from typing import IO

import pandas as pd

HR_REQUIRED_COLUMNS = [
    "employee_id", "name", "department", "designation",
    "status", "joining_date", "termination_date",
]
ACCOUNT_REQUIRED_COLUMNS = [
    "user_id", "employee_id", "username", "role", "account_status",
    "created_date", "last_login_date", "status_last_updated",
]
SYSTEM_FILES = {
    "core_banking": "core_banking_users.csv",
    "loan_system": "loan_system_users.csv",
    "database": "database_users.csv",
}
HR_FILE = "hr_employees.csv"
ACTIVE_ACCOUNT_STATUSES = {"active", "enabled"}


class DataValidationError(ValueError):
    pass


def read_csv(source: str | Path | IO) -> pd.DataFrame:
    df = pd.read_csv(source, dtype=str, keep_default_na=False)
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def validate_columns(df: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise DataValidationError(f"{label} is missing required column(s): {', '.join(missing)}")


def _clean_text(series: pd.Series) -> pd.Series:
    cleaned = series.fillna("").astype(str).str.strip()
    return cleaned.where(cleaned != "", None)


def _parse_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def normalize_hr(df: pd.DataFrame) -> pd.DataFrame:
    validate_columns(df, HR_REQUIRED_COLUMNS, "HR file")
    df = df[HR_REQUIRED_COLUMNS].copy()
    for col in ["employee_id", "name", "department", "designation", "status"]:
        df[col] = _clean_text(df[col])
    df["status"] = df["status"].str.title()
    for col in ["joining_date", "termination_date"]:
        df[col] = _parse_dates(df[col])
    df = df[df["employee_id"].notna()].drop_duplicates(subset="employee_id")
    return df.reset_index(drop=True)


def normalize_accounts(df: pd.DataFrame, label: str = "System user file") -> pd.DataFrame:
    validate_columns(df, ACCOUNT_REQUIRED_COLUMNS, label)
    df = df[ACCOUNT_REQUIRED_COLUMNS].copy()
    for col in ["user_id", "employee_id", "username", "role", "account_status"]:
        df[col] = _clean_text(df[col])
    df["account_status"] = df["account_status"].str.title()
    for col in ["created_date", "last_login_date", "status_last_updated"]:
        df[col] = _parse_dates(df[col])
    df["is_active"] = df["account_status"].str.lower().isin(ACTIVE_ACCOUNT_STATUSES)
    return df.reset_index(drop=True)


def load_review_data(data_dir: str | Path) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    data_dir = Path(data_dir)
    hr = normalize_hr(read_csv(data_dir / HR_FILE))
    systems = {
        system: normalize_accounts(read_csv(data_dir / filename), filename)
        for system, filename in SYSTEM_FILES.items()
        if (data_dir / filename).exists()
    }
    return hr, systems
