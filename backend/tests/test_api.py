"""API tests: auth, role-based access, validation, ticket lifecycle and AI-down behaviour.

Runs with GROQ_API_KEY empty (see conftest.py), so it also proves the app works with no AI at all.
"""

API = "/api/v1"


def test_health(app_client):
    body = app_client.get(f"{API}/health").json()
    assert body == {"status": "ok", "database": "connected", "ai": "fallback-only"}


def test_requires_login(app_client):
    r = app_client.get(f"{API}/books")
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHORIZED"


def test_wrong_password_is_generic(app_client):
    r = app_client.post(f"{API}/auth/login", json={"email": "a1@test.com", "password": "nope"})
    assert r.status_code == 401 and r.json()["error"]["message"] == "Invalid email or password"


def test_signup_creates_author_with_empty_account(app_client):
    body = {"name": "New Writer", "email": "New.Writer@test.com", "password": "longenough"}
    r = app_client.post(f"{API}/auth/register", json=body)
    assert r.status_code == 201
    user = r.json()["user"]
    assert user["role"] == "AUTHOR" and user["author_id"].startswith("AUTH") and user["email"] == "new.writer@test.com"
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    app_client.cookies.clear()
    assert app_client.get(f"{API}/books", headers=headers).json() == []
    assert app_client.post(f"{API}/auth/register", json=body).status_code == 409  # duplicate email
    app_client.cookies.clear()
    weak = app_client.post(f"{API}/auth/register", json={**body, "email": "x@test.com", "password": "short"})
    assert weak.status_code == 422 and "password" in weak.json()["error"]["details"]
    # Sign-up can never create an admin
    r = app_client.post(f"{API}/auth/register", json={**body, "email": "y@test.com", "role": "ADMIN"})
    assert r.status_code == 422


def test_author_sees_only_own_books(author1, author2):
    assert [b["id"] for b in author1.get(f"{API}/books").json()] == ["B1"]
    wip = author2.get(f"{API}/books").json()[0]
    assert wip["is_published"] is False and wip["production_stage"] == "Typesetting" and wip["mrp"] is None


def test_role_guards(author1, admin):
    assert author1.get(f"{API}/admin/tickets").status_code == 403
    assert admin.get(f"{API}/books").status_code == 403


def test_validation_errors_are_per_field(author1):
    r = author1.post(f"{API}/tickets", json={"subject": "Hi", "description": "short"})
    assert r.status_code == 422
    assert set(r.json()["error"]["details"]) == {"subject", "description"}


def test_cannot_file_ticket_on_someone_elses_book(author1):
    r = author1.post(f"{API}/tickets", json={"book_id": "B2", "subject": "About my book", "description": "x" * 30})
    assert r.status_code == 404


def test_full_ticket_lifecycle_without_ai(author1, author2, admin):
    # Author creates: instant rule-based triage, even with AI unavailable
    r = author1.post(f"{API}/tickets", json={
        "book_id": "B1", "subject": "Royalty not received",
        "description": "I haven't received any royalty for 6 months, please check.",
    })
    assert r.status_code == 201
    number = r.json()["ticket_number"]
    detail = admin.get(f"{API}/admin/tickets/{number}").json()
    assert detail["category"] == "ROYALTY_PAYMENTS" and detail["classified_by"] == "RULES"

    # Other authors can't see it
    assert author2.get(f"{API}/tickets/{number}").status_code == 404

    # AI draft unavailable -> clear 503, not a crash
    r = admin.post(f"{API}/admin/tickets/{number}/draft")
    assert r.status_code == 503 and r.json()["error"]["code"] == "AI_UNAVAILABLE"

    # Admin override is recorded
    r = admin.patch(f"{API}/admin/tickets/{number}", json={"priority": "CRITICAL"})
    assert r.json()["priority"] == "CRITICAL" and r.json()["classified_by"] == "ADMIN"

    # Internal note stays internal; reply is visible and moves the ticket forward
    admin.post(f"{API}/admin/tickets/{number}/messages", json={"body": "internal only", "internal": True})
    r = admin.post(f"{API}/admin/tickets/{number}/messages", json={"body": "Hi Asha, we're on it."})
    assert r.json()["status"] == "IN_PROGRESS" and r.json()["assigned_to"]["name"] == "Admin"
    # The reply shows as unread in the author's list until they open the ticket
    listed = next(t for t in author1.get(f"{API}/tickets").json() if t["ticket_number"] == number)
    assert listed["unread_reply"] is True
    author_view = author1.get(f"{API}/tickets/{number}").json()
    assert [m["body"] for m in author_view["messages"]] == ["Hi Asha, we're on it."]
    assert author_view["unread_reply"] is False
    listed = next(t for t in author1.get(f"{API}/tickets").json() if t["ticket_number"] == number)
    assert listed["unread_reply"] is False

    # Resolve -> author follow-up re-opens; closed tickets reject replies
    admin.patch(f"{API}/admin/tickets/{number}", json={"status": "RESOLVED"})
    assert author1.post(f"{API}/tickets/{number}/messages", json={"body": "One more thing"}).json()["status"] == "OPEN"
    admin.patch(f"{API}/admin/tickets/{number}", json={"status": "CLOSED"})
    assert author1.post(f"{API}/tickets/{number}/messages", json={"body": "Hello?"}).status_code == 409


def test_queue_filters_and_order(author1, admin):
    author1.post(f"{API}/tickets", json={"subject": "Update my bio", "description": "Can I update my author bio please?"})
    author1.post(f"{API}/tickets", json={"book_id": "B1", "subject": "ISBN mismatch", "description": "Amazon shows a different ISBN than the print."})
    queue = admin.get(f"{API}/admin/tickets", params={"status": "UNRESOLVED"}).json()
    ranks = [{"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[t["priority"]] for t in queue]
    assert ranks == sorted(ranks)  # most urgent first
    isbn = admin.get(f"{API}/admin/tickets", params={"category": "ISBN_METADATA"}).json()
    assert isbn and all(t["category"] == "ISBN_METADATA" for t in isbn)
    assert admin.get(f"{API}/admin/tickets", params={"priority": "URGENT"}).status_code == 422
