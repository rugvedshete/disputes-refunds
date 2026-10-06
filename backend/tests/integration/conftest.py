"""Integration tests run against a REAL Postgres (Testcontainers) with the real Alembic migrations.
Set TEST_DATABASE_URL to reuse an existing Postgres instead of starting a container."""
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.db import get_db
from app.main import app
from app.models import User
from app.security import hash_password

BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def pg_url():
    external = os.getenv("TEST_DATABASE_URL")
    if external:
        yield external
        return
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", driver="psycopg") as pg:
        yield pg.get_connection_url()


@pytest.fixture(scope="session")
def engine(pg_url):
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")  # proves the migrations build the schema the models expect
    eng = create_engine(pg_url, pool_size=20)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture()
def client(engine, session_factory):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE audit_log, refunds, evidence, disputes, users RESTART IDENTITY CASCADE"))

    def override():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def login(client, session_factory):
    """login(email, role) -> auth headers. Creates the user on first use."""

    def _login(email: str, role: str = "customer") -> dict:
        with session_factory() as db:
            if not db.scalar(select(User).where(User.email == email)):
                db.add(User(email=email, password_hash=hash_password("password123"), role=role))
                db.commit()
        r = client.post("/auth/login", json={"email": email, "password": "password123"})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _login


@pytest.fixture()
def customer(login):
    return login("ana@example.com", "customer")


@pytest.fixture()
def other_customer(login):
    return login("luis@example.com", "customer")


@pytest.fixture()
def agent(login):
    return login("agent@example.com", "agent")
