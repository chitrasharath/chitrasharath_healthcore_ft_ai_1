from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.db import get_supabase_db
from app.domains.async_tasks import models as async_tasks_models  # noqa: F401
from app.domains.async_tasks.models import DeadLetterTask
from app.domains.async_tasks.service import (
    _CELERY_STATUS_MAP,
    get_task_status,
    list_dlq,
    record_dead_letter,
)
from app.main import app
from tests.auth_helpers import auth_headers

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="dlq_session")
def dlq_session_fixture(monkeypatch: pytest.MonkeyPatch):
    SQLModel.metadata.create_all(test_engine)
    monkeypatch.setattr("app.domains.async_tasks.service.supabase_engine", test_engine)
    yield test_engine
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(name="client")
def client_fixture(dlq_session):
    def override():
        with Session(dlq_session) as session:
            yield session

    app.dependency_overrides[get_supabase_db] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_celery_status_map_covers_ticket_vocabulary() -> None:
    assert _CELERY_STATUS_MAP["PENDING"] == "pending"
    assert _CELERY_STATUS_MAP["STARTED"] == "started"
    assert _CELERY_STATUS_MAP["RETRY"] == "started"
    assert _CELERY_STATUS_MAP["SUCCESS"] == "success"
    assert _CELERY_STATUS_MAP["FAILURE"] == "failure"


def test_get_task_status_maps_success(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = MagicMock()
    fake.state = "SUCCESS"
    fake.result = {"run_id": "abc", "rows_loaded": 3}
    monkeypatch.setattr(
        "app.domains.async_tasks.service.AsyncResult",
        lambda task_id, app=None: fake,
    )
    payload = get_task_status("tid-1")
    assert payload == {
        "task_id": "tid-1",
        "status": "success",
        "result": {"run_id": "abc", "rows_loaded": 3},
    }


def test_get_task_status_maps_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = MagicMock()
    fake.state = "FAILURE"
    fake.result = RuntimeError("boom")
    monkeypatch.setattr(
        "app.domains.async_tasks.service.AsyncResult",
        lambda task_id, app=None: fake,
    )
    payload = get_task_status("tid-2")
    assert payload["status"] == "failure"
    assert "boom" in payload["result"]


def test_record_dead_letter_and_list_dlq(dlq_session) -> None:
    record_dead_letter(
        task_id="celery-1",
        task_name="pipeline.run_telemetry_etl",
        attempt=3,
        error="RuntimeError('forced')",
        traceback="tb",
    )
    rows = list_dlq(limit=10)
    assert len(rows) == 1
    assert rows[0].task_id == "celery-1"
    assert rows[0].attempt == 3
    assert "forced" in rows[0].error

    with Session(dlq_session) as session:
        stored = session.exec(select(DeadLetterTask)).one()
        assert stored.created_at is not None


def test_enqueue_returns_202_and_passes_run_id_only(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.domains.telemetry.router.supabase_engine", object())

    delayed = MagicMock()
    delayed.id = "celery-task-xyz"
    task = MagicMock()
    task.delay = MagicMock(return_value=delayed)
    monkeypatch.setattr("services.tasks.run_telemetry_etl", task)

    # Import path used inside the endpoint
    import services.tasks as tasks_mod

    monkeypatch.setattr(tasks_mod, "run_telemetry_etl", task)

    headers = auth_headers(client)
    response = client.post(
        "/api/v1/telemetry/pipelines/runs/enqueue",
        headers=headers,
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["task_id"] == "celery-task-xyz"
    assert "run_id" in body
    task.delay.assert_called_once()
    args, kwargs = task.delay.call_args
    assert len(args) == 1
    assert isinstance(args[0], str)
    assert kwargs.get("_force_fail") is False


def test_enqueue_force_fail_flag(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.domains.telemetry.router.supabase_engine", object())
    delayed = MagicMock()
    delayed.id = "celery-fail"
    task = MagicMock()
    task.delay = MagicMock(return_value=delayed)
    import services.tasks as tasks_mod

    monkeypatch.setattr(tasks_mod, "run_telemetry_etl", task)

    headers = auth_headers(client)
    response = client.post(
        "/api/v1/telemetry/pipelines/runs/enqueue?force_fail=true",
        headers=headers,
    )
    assert response.status_code == 202
    assert task.delay.call_args.kwargs.get("_force_fail") is True


def test_dlq_endpoint_lists_rows(client: TestClient, dlq_session) -> None:
    with Session(dlq_session) as session:
        session.add(
            DeadLetterTask(
                task_id="t1",
                task_name="pipeline.run_telemetry_etl",
                attempt=3,
                error="err",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    headers = auth_headers(client)
    response = client.get("/api/v1/tasks/dlq", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["task_id"] == "t1"


def test_run_telemetry_etl_retry_countdown_increases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from celery.exceptions import Retry
    from services.tasks import BASE_BACKOFF_SECONDS, MAX_RETRIES, run_telemetry_etl

    monkeypatch.setattr(
        "data.pipelines.pipeline.telemetry_etl_flow",
        MagicMock(side_effect=RuntimeError("etl failed")),
    )

    countdowns: list[int] = []

    def capture_retry(self, exc=None, countdown=None, **_kwargs):
        countdowns.append(countdown)
        raise Retry(exc=exc, when=countdown)

    monkeypatch.setattr(run_telemetry_etl.__class__, "retry", capture_retry)

    run_telemetry_etl.push_request(id="tid-r0", retries=0)
    try:
        with pytest.raises(Retry):
            run_telemetry_etl.run(str(uuid4()))
    finally:
        run_telemetry_etl.pop_request()

    run_telemetry_etl.push_request(id="tid-r1", retries=1)
    try:
        with pytest.raises(Retry):
            run_telemetry_etl.run(str(uuid4()))
    finally:
        run_telemetry_etl.pop_request()

    assert countdowns == [
        BASE_BACKOFF_SECONDS * (2**0),
        BASE_BACKOFF_SECONDS * (2**1),
    ]
    assert countdowns[1] > countdowns[0]

    # Final attempt: no retry — original error propagates
    run_telemetry_etl.push_request(id="tid-final", retries=MAX_RETRIES)
    try:
        with pytest.raises(RuntimeError, match="etl failed"):
            run_telemetry_etl.run(str(uuid4()))
    finally:
        run_telemetry_etl.pop_request()
