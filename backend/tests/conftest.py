import os
import pytest

# Must be set before any app module is imported
os.environ["ADMIN_PASSWORD"] = "test-password"

from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# In-memory SQLite with StaticPool so all connections share the same DB instance
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Patch database module BEFORE app.main is imported so all references
# (engine, SessionLocal, get_db) point to the test engine.
import app.database as _db
_db.engine = test_engine
_db.SessionLocal = TestingSession

from app.main import app
from app.database import Base, get_db


def _override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_db


@pytest.fixture(autouse=True)
def reset_db():
    """Fresh schema for every test — no seed data, full isolation."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth():
    return {"X-Admin-Password": "test-password"}


# ── Reusable resource factories ─────────────────────────────────────────────

@pytest.fixture
def player(client, auth):
    r = client.post("/api/players", json={"name": "Jogador A"}, headers=auth)
    assert r.status_code == 201
    return r.json()


@pytest.fixture
def current_round(client, auth):
    r = client.post("/api/rounds/current", json={"label": "Rodada Teste"}, headers=auth)
    assert r.status_code == 201
    return r.json()


@pytest.fixture
def finalized_round(client, auth):
    r = client.post("/api/rounds", json={"label": "Rodada Histórica"}, headers=auth)
    assert r.status_code == 201
    return r.json()
