import os

# Must be set before app.db is imported, since the engine is created at import time.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["BCRYPT_ROUNDS"] = "4"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client():
    from app.db import Base, engine
    from app.main import app

    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(engine)


def login(client, username, password) -> dict:
    response = client.post("/auth/login", data={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def auditor_headers(client):
    from app.settings import settings
    return login(client, settings.auditor_username, settings.auditor_password)


@pytest.fixture
def viewer_headers(client):
    from app.settings import settings
    return login(client, settings.viewer_username, settings.viewer_password)
