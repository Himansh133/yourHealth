import os

os.environ.setdefault("COOKIE_SECURE", "false")  # TestClient talks plain http
os.environ["EMBEDDINGS_ENABLED"] = "false"  # tests use stand-in models, never the multi-GB real ones
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://yourhealth:yourhealth@localhost:5432/yourhealth_test",
)


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    with engine.begin() as conn:
        tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_user_client(db_session):
    """Returns a function that registers + logs in a user, giving a separate cookie jar per user."""
    clients = []

    def _make(email: str, password: str = "correct horse battery"):
        app.dependency_overrides[get_db] = lambda: db_session
        c = TestClient(app)
        resp = c.post("/api/v1/auth/register", json={"email": email, "password": password})
        assert resp.status_code == 201, resp.text
        resp = c.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.text
        clients.append(c)
        return c

    yield _make
    app.dependency_overrides.clear()
