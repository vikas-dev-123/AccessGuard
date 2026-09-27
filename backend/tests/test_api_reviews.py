import pytest

from tests.test_api_upload import upload_sample

AS_OF = "2026-09-27"


@pytest.fixture
def review(client, auditor_headers):
    upload_sample(client, auditor_headers)
    response = client.post("/reviews/run", json={"as_of_date": AS_OF}, headers=auditor_headers)
    assert response.status_code == 201, response.text
    return response.json()


def findings(client, headers, review_id, **params):
    response = client.get(f"/reviews/{review_id}/findings", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_run_without_data_returns_404(client, auditor_headers):
    response = client.post("/reviews/run", headers=auditor_headers)
    assert response.status_code == 404
    assert "Upload" in response.json()["detail"]


def test_run_review_stores_results(client, auditor_headers, review):
    assert review["total_findings"] == 159
    assert review["as_of_date"] == AS_OF
    assert review["run_by"] == "auditor"
    assert client.get(f"/reviews/{review['id']}", headers=auditor_headers).json() == review


def test_summary(client, viewer_headers, review):
    summary = client.get(f"/reviews/{review['id']}/summary", headers=viewer_headers).json()

    assert summary["total"] == 159
    assert summary["by_risk"] == {"High": 86, "Medium": 44, "Low": 18, "Informational": 11}
    assert summary["by_check"]["Terminated users with active access"] == 22
    assert sum(summary["by_system"].values()) == 159


def test_findings_filters(client, viewer_headers, review):
    rid = review["id"]

    assert findings(client, viewer_headers, rid)["total"] == 159
    assert findings(client, viewer_headers, rid, risk_rating="High")["total"] == 86

    sod = findings(client, viewer_headers, rid, check="sod_conflicts")
    assert sod["total"] == 19
    assert all(f["check_code"] == "sod_conflicts" for f in sod["items"])

    core = findings(client, viewer_headers, rid, system="core_banking")["items"]
    assert core and all("core_banking" in f["system"] for f in core)

    combined = findings(client, viewer_headers, rid, system="loan_system", check="late_revocation", risk_rating="Medium")
    assert all(f["system"] == "loan_system" and f["risk_rating"] == "Medium" for f in combined["items"])


def test_findings_search_and_paging(client, viewer_headers, review):
    rid = review["id"]
    hit = findings(client, viewer_headers, rid, search="BACKUP_ADMIN")["items"]
    assert hit and all("backup_admin" in (f["username"] + f["details"]).lower() for f in hit)

    page = findings(client, viewer_headers, rid, limit=10, offset=150)
    assert page["total"] == 159
    assert [f["finding_id"] for f in page["items"]] == [f"F-{i:04d}" for i in range(151, 160)]


def test_finding_shape(client, viewer_headers, review):
    item = findings(client, viewer_headers, review["id"], limit=1)["items"][0]
    assert set(item) == {"finding_id", "check_code", "check_name", "system", "employee_id",
                         "username", "details", "risk_rating", "detected_at"}


def test_invalid_filters_and_missing_review(client, viewer_headers, review):
    rid = review["id"]
    assert client.get(f"/reviews/{rid}/findings", params={"check": "nope"}, headers=viewer_headers).status_code == 422
    assert client.get(f"/reviews/{rid}/findings", params={"risk_rating": "Severe"}, headers=viewer_headers).status_code == 422
    assert client.get("/reviews/999/summary", headers=viewer_headers).status_code == 404


def test_run_specific_dataset(client, auditor_headers, review):
    response = client.post("/reviews/run", json={"dataset_id": 42}, headers=auditor_headers)
    assert response.status_code == 404
