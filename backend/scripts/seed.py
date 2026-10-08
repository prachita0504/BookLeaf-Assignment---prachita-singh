"""Seeds MongoDB from data/bookleaf_sample_data.json: 10 authors, 18 books, admin users and demo tickets.

Run from backend/:
    python -m scripts.seed           # reset + seed (demo tickets triaged by keyword rules)
    python -m scripts.seed --ai      # also run AI classification on the demo tickets (uses Groq)

WARNING: drops the users, books, tickets, counters and ai_call_logs collections first.
"""

import argparse
import asyncio
import json
import os
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values

from app.ai import fallback
from app.core import database
from app.core.database import Collections
from app.core.security import hash_password
from app.schemas.common import PRIORITY_RANK, ClassifiedBy, MessageKind, Role, TicketStatus
from app.services import ticket_service
from app.utils.dates import utcnow

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "bookleaf_sample_data.json"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

# Login credentials come from backend/.env (see .env.example), never from code. Real environment
# variables take precedence over the file, which is how a hosting platform would supply them.
ENV = {**dotenv_values(ENV_FILE), **os.environ}
DEFAULT_AUTHOR_PASSWORD = ENV.get("AUTHOR_PASSWORD") or "author123"
ADMINS = [
    {
        "_id": "admin-1",
        "name": ENV.get("ADMIN_NAME") or "Admin",
        "email": (ENV.get("ADMIN_EMAIL") or "admin@gmail.com").lower(),
        "password": ENV.get("ADMIN_PASSWORD") or "admin123",
    },
]


def author_login(author: dict) -> tuple[str, str]:
    """Email + password for a dataset author: AUTHxxx_EMAIL / AUTHxxx_PASSWORD from .env if set,
    otherwise the email from the JSON and the default author password."""
    aid = author["author_id"]
    return (ENV.get(f"{aid}_EMAIL") or author["email"]).lower(), ENV.get(f"{aid}_PASSWORD") or DEFAULT_AUTHOR_PASSWORD

# Demo tickets covering every category, priority level and lifecycle state.
# AUTH006 and AUTH008 are deliberately left without tickets (empty-state testing).
DEMO_TICKETS = [
    {
        "author_id": "AUTH003", "book_id": "BK005", "hours_ago": 30,
        "subject": "Still no royalty for Between Two Temples",
        "description": "My book was published in July 2024 and has sold 67 copies, but I have not received a single "
        "rupee in royalty so far. My dashboard shows ₹2,546 pending. It has been more than a year now. "
        "Can someone please explain what is going on?",
    },
    {
        "author_id": "AUTH002", "book_id": "BK003", "hours_ago": 5,
        "subject": "ISBN on Amazon doesn't match my printed copy",
        "description": "The ISBN shown on the Amazon India listing for Code & Karma is different from the ISBN printed "
        "on the back cover of my physical copies. Readers are confused and I'm worried sales are being "
        "attributed to the wrong book.",
    },
    {
        "author_id": "AUTH007", "book_id": "BK013", "hours_ago": 72, "status": TicketStatus.IN_PROGRESS,
        "subject": "Cover design for Midnight in Mysore taking too long",
        "description": "It has been almost three weeks and my book is still in the cover design stage. When can I "
        "expect to see the cover options? I'm planning a launch event and need a date.",
        "thread": [
            ("ADMIN", MessageKind.REPLY, 60,
             "Hi Sneha, thank you for your patience, and we completely understand you're planning a launch. Your "
             "cover is with our design team now; we'll share the first two concepts with you within 48 hours.\n\n"
             "Warm regards,\nBookLeaf Author Support"),
            ("ADMIN", MessageKind.NOTE, 59, "Checked with design: concepts 80% done, designer was on leave last week."),
            ("AUTHOR", MessageKind.REPLY, 6,
             "Thanks. It's been more than 48 hours though and I still haven't received anything. Could you check again?"),
        ],
    },
    {
        "author_id": "AUTH004", "book_id": "BK006", "hours_ago": 50,
        "subject": "Blurry images and misaligned pages in author copies",
        "description": "I received 20 author copies of Debugging Life yesterday. The diagrams in chapter 3 are blurry "
        "and several pages are misaligned. I can't give these copies to anyone at my book signing.",
    },
    {
        "author_id": "AUTH010", "book_id": "BK018", "hours_ago": 20,
        "subject": "Howrah Nights shows 'Currently Unavailable' on Amazon",
        "description": "My book Howrah Nights is published but the Amazon India page says 'Currently unavailable'. "
        "Friends are trying to buy it and can't. How long will this take to fix?",
    },
    {
        "author_id": "AUTH001", "book_id": None, "hours_ago": 96, "status": TicketStatus.RESOLVED,
        "subject": "Can I update my author bio?",
        "description": "Hi team, I'd like to update my author bio on the BookLeaf Store and Amazon to mention my new "
        "award. How can I do that?",
        "thread": [
            ("ADMIN", MessageKind.REPLY, 90,
             "Hi Priya, congratulations on the award! You can submit the updated bio through your dashboard "
             "(Profile → Author Bio) or simply reply here with the new text. Changes typically reflect on all "
             "platforms within 3–5 business days.\n\nWarm regards,\nBookLeaf Author Support"),
            ("AUTHOR", MessageKind.REPLY, 80, "Done, submitted through the dashboard. Thank you!"),
        ],
    },
    {
        "author_id": "AUTH009", "book_id": "BK016", "hours_ago": 26,
        "subject": "Why hasn't my ₹850 royalty been paid?",
        "description": "The Nagpur Notebooks shows ₹850 royalty pending but I haven't received any payment yet. When "
        "will this be transferred to my bank account?",
    },
    {
        "author_id": "AUTH005", "book_id": "BK009", "hours_ago": 7,
        "subject": "Royalty for Letters from Lakshadweep seems low",
        "description": "I have sold 201 copies of Letters from Lakshadweep at ₹550 each but my total royalty is only "
        "₹11,055. That seems far too low. Can you explain how this is calculated?",
    },
]


def _message(sender: dict, role: Role, kind: MessageKind, body: str, created_at) -> dict:
    return {
        "id": uuid4().hex, "kind": kind, "sender_id": sender["_id"], "sender_role": role,
        "sender_name": sender["name"], "body": body, "ai_assisted": False, "created_at": created_at,
    }


async def seed(run_ai: bool) -> None:
    await database.connect()
    db = database.get_db()
    for name in (Collections.USERS, Collections.BOOKS, Collections.TICKETS, Collections.COUNTERS, Collections.AI_CALL_LOGS):
        await db[name].drop()
    await database.ensure_indexes()

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    now = utcnow()

    users, books = [], []
    for a in data["authors"]:
        email, password = author_login(a)
        users.append({
            "_id": f"user-{a['author_id'].lower()}",
            "email": email,
            "password_hash": hash_password(password),
            "name": a["name"], "role": Role.AUTHOR, "author_id": a["author_id"], "phone": a.get("phone"),
            "city": a.get("city"), "joined_date": a.get("joined_date"), "created_at": now,
        })
        for b in a["books"]:
            books.append({"_id": b.pop("book_id"), "author_id": a["author_id"], **b})
    users += [
        {
            "_id": adm["_id"], "name": adm["name"], "email": adm["email"], "password_hash": hash_password(adm["password"]),
            "role": Role.ADMIN, "author_id": None, "created_at": now,
        }
        for adm in ADMINS
    ]

    await db[Collections.USERS].insert_many(users)
    await db[Collections.BOOKS].insert_many(books)

    users_by_author = {u["author_id"]: u for u in users if u["author_id"]}
    books_by_id = {b["_id"]: b for b in books}
    admin = ADMINS[0]

    tickets = []
    for number, t in enumerate(DEMO_TICKETS, start=1001):
        author = users_by_author[t["author_id"]]
        book = books_by_id.get(t["book_id"]) if t["book_id"] else None
        rules = fallback.classify(t["subject"], t["description"], book["status"] if book else None)
        created = now - timedelta(hours=t["hours_ago"])
        messages = [
            _message(admin if who == "ADMIN" else author, Role(who), kind, body, now - timedelta(hours=h))
            for who, kind, h, body in t.get("thread", [])
        ]
        first_reply = next((m["created_at"] for m in messages if m["sender_role"] == Role.ADMIN and m["kind"] == MessageKind.REPLY), None)
        status = t.get("status", TicketStatus.OPEN)
        tickets.append({
            "_id": number, "author_id": t["author_id"], "author_name": author["name"], "book_id": t["book_id"],
            "subject": t["subject"], "description": t["description"], "attachment_name": None,
            "status": status, "category": rules.category, "priority": rules.priority,
            "priority_rank": PRIORITY_RANK[rules.priority], "classified_by": ClassifiedBy.RULES,
            "rules": {"category": rules.category, "priority": rules.priority, "reason": rules.reason},
            "ai": None, "ai_draft": None,
            "assigned_to": {"id": admin["_id"], "name": admin["name"]} if messages else None,
            "messages": messages, "first_response_at": first_reply,
            "resolved_at": messages[-1]["created_at"] if status == TicketStatus.RESOLVED else None,
            "created_at": created, "updated_at": messages[-1]["created_at"] if messages else created,
            "last_activity_at": messages[-1]["created_at"] if messages else created,
            # Demo threads start as already read by the author (no stale "new reply" badges).
            "author_last_read_at": messages[-1]["created_at"] if messages else None,
        })
    await db[Collections.TICKETS].insert_many(tickets)
    await db[Collections.COUNTERS].insert_many([
        {"_id": "ticket_number", "seq": len(tickets)},
        {"_id": "author_id", "seq": len(data["authors"])},  # sign-ups continue from AUTH011
    ])

    print(f"Seeded {len(users) - len(ADMINS)} authors, {len(ADMINS)} admins, {len(books)} books, {len(tickets)} tickets")

    if run_ai:
        print("Running AI triage on demo tickets...")
        for t in tickets:
            await ticket_service.run_ai_triage(t["_id"])
            doc = await db[Collections.TICKETS].find_one({"_id": t["_id"]})
            print(f"  #{t['_id']}: rules={t['category']}/{t['priority']} -> now {doc['category']}/{doc['priority']} ({doc['classified_by']})")

    await database.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ai", action="store_true", help="classify demo tickets with the LLM")
    asyncio.run(seed(parser.parse_args().ai))
