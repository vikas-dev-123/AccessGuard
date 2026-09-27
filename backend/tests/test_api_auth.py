import io

from app.settings import settings


def test_login_returns_token_and_role(client):
    response = client.post("/auth/login", data={"username": settings.auditor_username,
                                                "password": settings.auditor_password})
    body = response.json()

    assert response.status_code == 200
    assert body["role"] == "auditor"
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_wrong_password_rejected(client):
    response = client.post("/auth/login", data={"username": settings.auditor_username, "password": "nope"})
    assert response.status_code == 401


def test_me_returns_current_user(client, viewer_headers):
    response = client.get("/auth/me", headers=viewer_headers)
    assert response.json()["role"] == "viewer"


def test_endpoints_require_token(client):
    assert client.get("/reviews").status_code == 401
    assert client.get("/reviews", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401


def test_viewer_cannot_upload_or_run(client, viewer_headers):
    files = {"hr_file": ("hr.csv", io.BytesIO(b"x"), "text/csv")}
    assert client.post("/upload", files=files, headers=viewer_headers).status_code == 403
    assert client.post("/reviews/run", headers=viewer_headers).status_code == 403


def test_viewer_can_read(client, viewer_headers):
    assert client.get("/reviews", headers=viewer_headers).status_code == 200
    assert client.get("/checks", headers=viewer_headers).status_code == 200
