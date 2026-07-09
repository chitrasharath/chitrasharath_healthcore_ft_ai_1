from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "30")
# Force stdout reset-link fallback; dev .env may set EMAIL_API_KEY for Resend sandbox.
os.environ["EMAIL_API_KEY"] = ""
os.environ.setdefault("DATABASE_URL", "")
os.environ["DATABASE_URL"] = ""

from app.core.db import get_supabase_db  # noqa: E402
from app.domains.telemetry import models as telemetry_models  # noqa: E402, F401
from app.main import app  # noqa: E402

telemetry_test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="telemetry_session")
def telemetry_session_fixture():
    SQLModel.metadata.create_all(telemetry_test_engine)
    yield telemetry_test_engine
    SQLModel.metadata.drop_all(telemetry_test_engine)


@pytest.fixture(name="telemetry_client")
def telemetry_client_fixture(telemetry_session):
    def override():
        with Session(telemetry_session) as session:
            yield session

    app.dependency_overrides[get_supabase_db] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
