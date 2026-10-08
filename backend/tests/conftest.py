"""Test setup: API tests run against a separate `<db>_test` database with AI disabled
(so they're fast, free and deterministic, and they also exercise the no-AI fallback path)."""

import os

os.environ["GROQ_API_KEY"] = ""  # must be set before the app's settings are first loaded

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.config import get_settings
from app.core.security import hash_password

settings = get_settings()
TEST_DB = f"{settings.mongodb_db}_test"
settings.mongodb_db = TEST_DB


@pytest.fixture(scope="session")
def seeded_db():
    client = MongoClient(settings.mongodb_uri, tz_aware=True)
    client.drop_database(TEST_DB)
    db = client[TEST_DB]
    pw = hash_password("pass1234")
    db.users.insert_many([
        {"_id": "u-a1", "email": "a1@test.com", "password_hash": pw, "name": "Asha One", "role": "AUTHOR", "author_id": "A1"},
        {"_id": "u-a2", "email": "a2@test.com", "password_hash": pw, "name": "Bina Two", "role": "AUTHOR", "author_id": "A2"},
        {"_id": "u-adm", "email": "admin@test.com", "password_hash": pw, "name": "Admin", "role": "ADMIN", "author_id": None},
    ])
    base = {"genre": "Fiction", "available_on": [], "print_partner": None, "author_royalty_per_copy": None,
            "last_royalty_payout_date": None, "total_copies_sold": 0, "total_royalty_earned": 0,
            "royalty_paid": 0, "royalty_pending": 0}
    db.books.insert_many([
        {**base, "_id": "B1", "author_id": "A1", "title": "Live Book", "isbn": "111", "status": "Published & Live",
         "publication_date": "2024-01-01", "mrp": 300, "royalty_pending": 850},
        {**base, "_id": "B2", "author_id": "A2", "title": "WIP Book", "isbn": "222",
         "status": "In Production - Typesetting", "publication_date": None, "mrp": None},
    ])
    yield db
    client.drop_database(TEST_DB)
    client.close()


@pytest.fixture(scope="session")
def app_client(seeded_db):
    from app.main import app

    with TestClient(app) as c:  # runs the lifespan (DB connect)
        yield c


class LoggedIn:
    """Sends requests through the one shared TestClient (one event loop, as the async Mongo client
    requires) as a specific user, via the Bearer-token path that API clients like Postman use."""

    def __init__(self, client: TestClient, token: str):
        self.client, self.headers = client, {"Authorization": f"Bearer {token}"}

    def get(self, url, **kw):
        return self.client.get(url, headers=self.headers, **kw)

    def post(self, url, **kw):
        return self.client.post(url, headers=self.headers, **kw)

    def patch(self, url, **kw):
        return self.client.patch(url, headers=self.headers, **kw)


def _login(app_client: TestClient, email: str) -> LoggedIn:
    r = app_client.post("/api/v1/auth/login", json={"email": email, "password": "pass1234"})
    assert r.status_code == 200, r.text
    app_client.cookies.clear()  # keep the shared client anonymous; identity comes from the header
    return LoggedIn(app_client, r.json()["access_token"])


@pytest.fixture(scope="session")
def author1(app_client):
    return _login(app_client, "a1@test.com")


@pytest.fixture(scope="session")
def author2(app_client):
    return _login(app_client, "a2@test.com")


@pytest.fixture(scope="session")
def admin(app_client):
    return _login(app_client, "admin@test.com")
