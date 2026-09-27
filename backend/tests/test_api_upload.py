import io

import pandas as pd

from app.config import BACKEND_DIR
from app.data_loading import ACCOUNT_REQUIRED_COLUMNS, HR_REQUIRED_COLUMNS
from tests.helpers import account, employee

DATA_DIR = BACKEND_DIR / "data"


def csv_bytes(rows, columns) -> bytes:
    return pd.DataFrame(rows, columns=columns).to_csv(index=False).encode()


def file_tuple(name, content: bytes):
    return (name, io.BytesIO(content), "text/csv")


def sample_files():
    names = {
        "hr_file": "hr_employees.csv",
        "core_banking_file": "core_banking_users.csv",
        "loan_system_file": "loan_system_users.csv",
        "database_file": "database_users.csv",
    }
    return {field: file_tuple(name, (DATA_DIR / name).read_bytes()) for field, name in names.items()}


def upload_sample(client, headers):
    response = client.post("/upload", files=sample_files(), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def errors_of(response) -> list[dict]:
    assert response.status_code == 422, response.text
    return response.json()["detail"]["errors"]


def test_upload_sample_data(client, auditor_headers):
    body = upload_sample(client, auditor_headers)

    assert body["hr_employee_count"] == 200
    assert body["systems"] == ["core_banking", "loan_system", "database"]
    assert body["account_counts"] == {"core_banking": 100, "loan_system": 60, "database": 145}
    assert body["uploaded_by"] == "auditor"

    listed = client.get("/datasets", headers=auditor_headers).json()
    assert [d["id"] for d in listed] == [body["id"]]


def test_hr_only_upload_is_rejected(client, auditor_headers):
    files = {"hr_file": file_tuple("hr.csv", csv_bytes([employee("E1")], HR_REQUIRED_COLUMNS))}
    errors = errors_of(client.post("/upload", files=files, headers=auditor_headers))
    assert "at least one system user list" in errors[0]["error"]


def test_missing_columns_are_named(client, auditor_headers):
    hr = csv_bytes([employee("E1")], HR_REQUIRED_COLUMNS)
    bad_accounts = pd.DataFrame([account("C1", "E1", "Teller")]).drop(columns=["username", "role"])
    files = {
        "hr_file": file_tuple("hr.csv", hr),
        "core_banking_file": file_tuple("core.csv", bad_accounts.to_csv(index=False).encode()),
    }
    errors = errors_of(client.post("/upload", files=files, headers=auditor_headers))

    assert len(errors) == 1
    assert errors[0]["file"] == "core.csv"
    assert "username, role" in errors[0]["error"]


def test_row_level_problems_reported_across_files(client, auditor_headers):
    hr = csv_bytes([
        employee("E1"),
        employee("E1"),                                  # duplicate id
        employee("E2", status="Retired"),                # invalid status
        employee("E3", joining_date="31/12/2020"),       # wrong date format
        employee("E4", status="Terminated"),             # no termination date
    ], HR_REQUIRED_COLUMNS)
    accounts = csv_bytes([account("C1", "E1", "Teller", username=" ")], ACCOUNT_REQUIRED_COLUMNS)
    files = {"hr_file": file_tuple("hr.csv", hr), "loan_system_file": file_tuple("loan.csv", accounts)}

    errors = errors_of(client.post("/upload", files=files, headers=auditor_headers))
    messages = " | ".join(f"{e['file']}: {e['error']}" for e in errors)

    assert "hr.csv: Duplicate 'employee_id' values at rows 2, 3" in messages
    assert "'status' must be Active or Terminated at row 4" in messages
    assert "'joining_date' is not a valid YYYY-MM-DD date at row 5" in messages
    assert "Terminated employee has no termination_date at row 6" in messages
    assert "loan.csv: 'username' is blank at row 2" in messages


def test_non_csv_and_empty_files_rejected(client, auditor_headers):
    files = {
        "hr_file": file_tuple("hr.xlsx", b"PK\x03\x04"),
        "database_file": file_tuple("db.csv", b""),
    }
    errors = errors_of(client.post("/upload", files=files, headers=auditor_headers))

    assert {"file": "hr.xlsx", "error": "File must be a .csv file."} in errors
    assert {"file": "db.csv", "error": "File is empty."} in errors


def test_header_only_file_rejected(client, auditor_headers):
    files = {
        "hr_file": file_tuple("hr.csv", ",".join(HR_REQUIRED_COLUMNS).encode()),
        "database_file": file_tuple("db.csv", csv_bytes([account("D1", "E1", "DBA")], ACCOUNT_REQUIRED_COLUMNS)),
    }
    errors = errors_of(client.post("/upload", files=files, headers=auditor_headers))
    assert errors == [{"file": "hr.csv", "error": "File has a header row but no data rows."}]
