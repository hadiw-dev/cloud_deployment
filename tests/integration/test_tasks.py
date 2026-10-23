"""Run against an explicitly supplied, disposable, migrated PostgreSQL database.

No table drops, truncation, or production DATABASE_URL fallback are performed.
"""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import build_engine
from app.main import create_app
from app.models import Task

pytestmark = pytest.mark.integration


@pytest.fixture
def database_url():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to an isolated, migrated PostgreSQL database")
    return url


def test_crud_and_persistence(database_url):
    settings = Settings(database_url=database_url)
    task_id = None
    try:
        with TestClient(create_app(settings)) as client:
            assert client.get("/ready").status_code == 200
            assert client.get("/tasks/2147483647").status_code == 404
            created = client.post("/tasks", json={"title": f"integration-{uuid4()}"})
            assert created.status_code == 201
            task = created.json()
            task_id = task["id"]
            assert created.headers["location"] == f"/tasks/{task_id}"
            assert task["completed"] is False
            assert task["created_at"] and task["updated_at"]
            assert client.get(f"/tasks/{task_id}").json() == task
            assert task_id in [row["id"] for row in client.get("/tasks").json()]
            updated = client.put(f"/tasks/{task_id}", json={
                "title": "updated", "description": "persisted", "completed": True,
            })
            assert updated.status_code == 200
            assert updated.json()["completed"] is True
            assert updated.json()["created_at"] == task["created_at"]
            assert updated.json()["updated_at"] > task["updated_at"]
        # A new application/connection pool must still see committed data.
        with TestClient(create_app(settings)) as restarted:
            assert restarted.get(f"/tasks/{task_id}").json()["description"] == "persisted"
            # PUT replaces optional fields with defaults.
            replaced = restarted.put(f"/tasks/{task_id}", json={"title": "replacement"})
            assert replaced.json()["description"] is None
            assert replaced.json()["completed"] is False
            removed = restarted.delete(f"/tasks/{task_id}")
            assert removed.status_code == 204 and removed.content == b""
            assert restarted.get(f"/tasks/{task_id}").status_code == 404
            assert restarted.delete(f"/tasks/{task_id}").status_code == 404
            assert restarted.put(f"/tasks/{task_id}", json={"title": "missing"}).status_code == 404
    finally:
        if task_id is not None:
            engine = build_engine(database_url)
            try:
                with Session(engine) as session:
                    session.execute(delete(Task).where(Task.id == task_id))
                    session.commit()
            finally:
                engine.dispose()
