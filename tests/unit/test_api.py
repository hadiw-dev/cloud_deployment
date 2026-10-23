import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.config import Settings
from app.database import get_session
from app.main import create_app
from app.schemas import TaskWrite

pytestmark = pytest.mark.unit


@pytest.fixture
def client():
    settings = Settings(database_url="postgresql+psycopg://unused:unused@127.0.0.1:1/unused")
    with TestClient(create_app(settings)) as client:
        yield client


def test_liveness_does_not_require_database(client):
    assert client.get("/health").json() == {"status": "ok"}

    def unavailable_session():
        raise OperationalError("connection refused", {}, Exception("unavailable"))

    client.app.dependency_overrides[get_session] = unavailable_session
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
    assert "unused" not in response.text


@pytest.mark.parametrize("title", ["", "   ", "x" * 201])
def test_invalid_titles(client, title):
    response = client.post("/tasks", json={"title": title})
    assert response.status_code == 422
    assert "input" not in response.json()["detail"][0]


def test_payload_rules():
    assert TaskWrite(title="  deploy  ").title == "deploy"
    with pytest.raises(ValidationError):
        TaskWrite(title="deploy", description="x" * 10001)
    with pytest.raises(ValidationError):
        TaskWrite(title="deploy", unexpected="value")


def test_config_requires_postgres_and_redacts_secret():
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///test.db")
    config = Settings(database_url="postgresql+psycopg://user:private-value@db/tasks")
    assert "private-value" not in repr(config)


def test_database_errors_are_sanitized(client):
    def fail_session():
        raise OperationalError("sensitive SQL", {}, Exception("secret password"))

    client.app.dependency_overrides[get_session] = fail_session
    response = client.get("/tasks")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}


def test_positive_identifiers(client):
    assert client.get("/tasks/0").status_code == 422
    assert client.get("/tasks/2147483648").status_code == 422
    assert client.get("/tasks/not-an-id").status_code == 422
