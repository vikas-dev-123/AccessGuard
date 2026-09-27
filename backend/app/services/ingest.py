"""Validates uploaded CSVs and stores them as a Dataset."""
from __future__ import annotations

import io
from dataclasses import dataclass

import pandas as pd
from sqlalchemy.orm import Session

from app.data_loading import (
    ACCOUNT_REQUIRED_COLUMNS,
    HR_REQUIRED_COLUMNS,
    normalize_accounts,
    normalize_hr,
    read_csv,
)
from app.models import Dataset, HREmployee, SystemAccount
from app.settings import settings

HR_STATUSES = {"Active", "Terminated"}
DATE_FORMAT = "%Y-%m-%d"
MAX_ROWS_LISTED = 5


@dataclass
class UploadedFile:
    filename: str
    content: bytes


class UploadValidationError(Exception):
    def __init__(self, errors: list[dict]):
        super().__init__(f"{len(errors)} validation error(s)")
        self.errors = errors


def _rows(mask: pd.Series) -> str:
    # +2: row 1 is the header, and pandas indexes from 0.
    rows = [str(i + 2) for i in mask[mask].index]
    listed = ", ".join(rows[:MAX_ROWS_LISTED])
    extra = len(rows) - MAX_ROWS_LISTED
    label = "row" if len(rows) == 1 else "rows"
    return f"{label} {listed}" + (f" (and {extra} more)" if extra > 0 else "")


def _read(upload: UploadedFile) -> tuple[pd.DataFrame | None, list[str]]:
    if not upload.filename.lower().endswith(".csv"):
        return None, ["File must be a .csv file."]
    if len(upload.content) > settings.max_upload_bytes:
        return None, [f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB upload limit."]
    if not upload.content.strip():
        return None, ["File is empty."]
    try:
        text = upload.content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, ["File is not UTF-8 text. Re-export it as 'CSV UTF-8'."]
    try:
        return read_csv(io.StringIO(text)), []
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        return None, [f"Could not be parsed as CSV: {exc}"]


def _structure_errors(df: pd.DataFrame, required: list[str]) -> list[str]:
    missing = [c for c in required if c not in df.columns]
    if missing:
        return [f"Missing required column(s): {', '.join(missing)}. Expected columns: {', '.join(required)}."]
    if df.empty:
        return ["File has a header row but no data rows."]
    return []


def _blank_errors(df: pd.DataFrame, columns: list[str]) -> list[str]:
    errors = []
    for col in columns:
        blank = df[col].str.strip() == ""
        if blank.any():
            errors.append(f"'{col}' is blank at {_rows(blank)}.")
    return errors


def _date_errors(df: pd.DataFrame, columns: list[str]) -> list[str]:
    errors = []
    for col in columns:
        values = df[col].str.strip()
        parsed = pd.to_datetime(values, format=DATE_FORMAT, errors="coerce")
        bad = (values != "") & parsed.isna()
        if bad.any():
            errors.append(f"'{col}' is not a valid YYYY-MM-DD date at {_rows(bad)}.")
    return errors


def _duplicate_errors(df: pd.DataFrame, column: str) -> list[str]:
    values = df[column].str.strip()
    dup = values.duplicated(keep=False) & (values != "")
    return [f"Duplicate '{column}' values at {_rows(dup)}."] if dup.any() else []


def validate_hr(df: pd.DataFrame) -> list[str]:
    errors = _structure_errors(df, HR_REQUIRED_COLUMNS)
    if errors:
        return errors
    errors += _blank_errors(df, ["employee_id", "name", "status", "joining_date"])
    errors += _duplicate_errors(df, "employee_id")
    status = df["status"].str.strip().str.title()
    bad_status = (status != "") & ~status.isin(HR_STATUSES)
    if bad_status.any():
        errors.append(f"'status' must be Active or Terminated at {_rows(bad_status)}.")
    errors += _date_errors(df, ["joining_date", "termination_date"])
    no_term_date = (status == "Terminated") & (df["termination_date"].str.strip() == "")
    if no_term_date.any():
        errors.append(f"Terminated employee has no termination_date at {_rows(no_term_date)}.")
    return errors


def validate_accounts(df: pd.DataFrame) -> list[str]:
    errors = _structure_errors(df, ACCOUNT_REQUIRED_COLUMNS)
    if errors:
        return errors
    errors += _blank_errors(df, ["user_id", "username", "role", "account_status"])
    errors += _duplicate_errors(df, "user_id")
    errors += _date_errors(df, ["created_date", "last_login_date", "status_last_updated"])
    return errors


def parse_upload(hr_file: UploadedFile, system_files: dict[str, UploadedFile]) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Validate every file and collect all errors, so the user can fix everything in one go."""
    errors: list[dict] = []
    if not system_files:
        errors.append({"file": None, "error": "Upload at least one system user list alongside the HR file."})

    frames: dict[str, pd.DataFrame] = {}
    jobs = [("hr", hr_file, validate_hr)] + [(s, f, validate_accounts) for s, f in system_files.items()]
    for key, upload, validator in jobs:
        df, file_errors = _read(upload)
        if df is not None:
            file_errors = validator(df)
        errors += [{"file": upload.filename, "error": e} for e in file_errors]
        if df is not None and not file_errors:
            frames[key] = df

    if errors:
        raise UploadValidationError(errors)

    hr = normalize_hr(frames.pop("hr"))
    systems = {s: normalize_accounts(df, system_files[s].filename) for s, df in frames.items()}
    return hr, systems


def _date(value):
    return None if pd.isna(value) else value.date()


def save_dataset(db: Session, hr: pd.DataFrame, systems: dict[str, pd.DataFrame],
                 file_names: dict[str, str], uploaded_by: str) -> Dataset:
    dataset = Dataset(
        uploaded_by=uploaded_by,
        systems=list(systems),
        file_names=file_names,
        hr_employee_count=len(hr),
        account_counts={s: len(df) for s, df in systems.items()},
    )
    dataset.employees = [
        HREmployee(
            employee_id=r.employee_id, name=r.name, department=r.department, designation=r.designation,
            status=r.status, joining_date=_date(r.joining_date), termination_date=_date(r.termination_date),
        )
        for r in hr.itertuples(index=False)
    ]
    dataset.accounts = [
        SystemAccount(
            system=system, user_id=r.user_id, employee_id=r.employee_id, username=r.username,
            role=r.role, account_status=r.account_status, created_date=_date(r.created_date),
            last_login_date=_date(r.last_login_date), status_last_updated=_date(r.status_last_updated),
        )
        for system, df in systems.items()
        for r in df.itertuples(index=False)
    ]
    db.add(dataset)
    db.commit()
    return dataset
