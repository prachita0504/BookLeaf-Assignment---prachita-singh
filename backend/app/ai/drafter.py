"""AI response drafting using ticket text, the author's real book/royalty data and the relevant KB sections.

Drafts are cached on the ticket (see ticket_service.get_draft) so re-opening it costs no tokens.

Token budget per draft (approx.): system prompt 700–900 + account facts 100–250 + conversation
capped at ~1,200, so a draft prompt stays around 2k tokens no matter how long the thread grows.
"""

from datetime import date

from app.ai import client
from app.ai.prompts import draft_system_prompt, draft_user_message
from app.core.config import get_settings
from app.schemas.common import MIN_PAYOUT_THRESHOLD, Category, MessageKind, Role
from app.utils.dates import days_between, fmt_date, next_payout, parse_date

MAX_CONTEXT_MESSAGES = 6  # most recent messages only; older ones rarely change the reply
MAX_CHARS_PER_MESSAGE = 700
MAX_DESCRIPTION_CHARS = 2000
# One quarter (~91 days) + 45-day payout window: no payout for longer than this suggests a missed cycle.
PAYOUT_GAP_DAYS = 136


def book_facts(book: dict, today: date) -> list[str]:
    """Turns a book document into plain-language facts the model can quote."""
    lines = [f'Book: "{book["title"]}" (ISBN {book["isbn"]}, {book["genre"]})', f"Status: {book['status']}"]
    if book["status"] != "Published & Live":
        stage = book["status"].removeprefix("In Production - ")
        lines.append(
            f"Currently at the {stage} stage. Stages: Manuscript Received → Editing → Cover Design → Typesetting → "
            "Proofreading → ISBN Assignment → Printing → Distribution Setup → Published & Live."
        )
        lines.append("Not yet published, so no sales or royalties yet.")
        return lines

    pending = book.get("royalty_pending") or 0
    last_payout = parse_date(book.get("last_royalty_payout_date"))
    published = parse_date(book.get("publication_date"))
    lines += [
        f"Published: {fmt_date(published)}; MRP ₹{book.get('mrp')}",
        f"Author royalty per copy: ₹{book.get('author_royalty_per_copy')}. This is already the author's 80% share of net profit "
        "(MRP minus printing, platform commission and shipping, then the 80/20 split). It is NOT the net profit itself.",
        f"Copies sold: {book.get('total_copies_sold', 0)}",
        f"Royalty earned ₹{book.get('total_royalty_earned', 0):,} | paid ₹{book.get('royalty_paid', 0):,} | pending ₹{pending:,}",
        f"Last payout: {fmt_date(last_payout) if last_payout else 'no payout made yet'}",
        f"Available on: {', '.join(book.get('available_on') or []) or 'not listed yet'}; printed by {book.get('print_partner') or 'n/a'}",
    ]
    if 0 < pending < MIN_PAYOUT_THRESHOLD:
        lines.append(
            f"Pending royalty ₹{pending:,} is below the ₹{MIN_PAYOUT_THRESHOLD:,} minimum payout threshold. It is NOT overdue: "
            f"it keeps rolling over and is paid in the first quarterly payout after the accumulated total reaches ₹{MIN_PAYOUT_THRESHOLD:,}. "
            "It will not be paid in the next payout unless new sales take it over the threshold."
        )
    elif pending >= MIN_PAYOUT_THRESHOLD:
        reference = last_payout or published
        if reference and days_between(reference, today) > PAYOUT_GAP_DAYS:
            lines.append(
                f"FLAG: ₹{pending:,} is pending and it has been {days_between(reference, today)} days since "
                f"{'the last payout' if last_payout else 'publication'}, longer than one quarterly cycle + 45 days. "
                "At least one earlier quarterly payout appears to have been missed, so this looks overdue: BookLeaf "
                "should own it and escalate (update within 48 hours). Do not describe the upcoming payout date as missed."
            )
    return lines


def account_facts(*, author: dict, book: dict | None, author_books: list[dict], today: date) -> str:
    payout = next_payout(today)
    lines = [
        f"Today: {fmt_date(today)}",
        f"Author: {author['name']} (first name: {author['name'].split()[0]}), BookLeaf author since {author.get('joined_date') or 'n/a'}",
        f"Next scheduled royalty payout run (still upcoming): by {fmt_date(payout['pay_by'])}, for the quarter that "
        f"ended {fmt_date(payout['quarter_end'])} ({payout['quarter']})",
    ]
    if book:
        lines += book_facts(book, today)
    elif author_books:
        # Account-level ticket: a compact one-line summary per book instead of full details.
        lines.append("Ticket is account-level (no specific book). The author's books:")
        for b in author_books:
            lines.append(
                f'- "{b["title"]}": {b["status"]}; sold {b.get("total_copies_sold", 0)}; '
                f"pending ₹{b.get('royalty_pending', 0):,}; last payout {b.get('last_royalty_payout_date') or 'none'}"
            )
    return "\n".join(lines)


def conversation_text(messages: list[dict]) -> str:
    # Internal notes are deliberately NOT sent to the model. A prompt instruction like "don't reveal
    # notes" proved unreliable in testing, so this privacy guarantee is enforced in code instead.
    messages = [m for m in messages if m["kind"] == MessageKind.REPLY]
    recent = messages[-MAX_CONTEXT_MESSAGES:]
    parts = []
    if len(messages) > len(recent):
        parts.append(f"({len(messages) - len(recent)} earlier messages omitted)")
    for m in recent:
        body = m["body"][:MAX_CHARS_PER_MESSAGE] + ("…" if len(m["body"]) > MAX_CHARS_PER_MESSAGE else "")
        who = "AUTHOR" if m["sender_role"] == Role.AUTHOR else "BOOKLEAF SUPPORT"
        parts.append(f"[{who}] {body}")
    return "\n\n".join(parts)


async def generate_draft(*, ticket: dict, author: dict, book: dict | None, author_books: list[dict], today: date) -> str:
    settings = get_settings()
    category = Category(ticket["category"])
    return await client.complete(
        task="DRAFT",
        model=settings.groq_draft_model,
        system=draft_system_prompt(category),
        user=draft_user_message(
            account_facts=account_facts(author=author, book=book, author_books=author_books, today=today),
            subject=ticket["subject"],
            description=ticket["description"][:MAX_DESCRIPTION_CHARS],
            conversation=conversation_text(ticket.get("messages", [])),
        ),
        max_tokens=1200,  # ~220-word reply + the reasoning model's thinking tokens
        temperature=0.4,  # some warmth/variation, still grounded
        ticket_number=ticket["_id"],
    )
