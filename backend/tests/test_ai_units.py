"""Offline unit tests for the AI layer: fallback rules, output validation, prompt context, payout dates."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.ai import drafter, fallback
from app.ai.classifier import AIClassification
from app.ai.knowledge_base import KB_SECTIONS, kb_for_category
from app.schemas.common import Category, Priority
from app.utils.dates import next_payout


@pytest.mark.parametrize(
    "subject, description, category, priority",
    [
        ("No royalty", "I haven't received any royalty for 6 months.", Category.ROYALTY_PAYMENTS, Priority.CRITICAL),
        ("ISBN problem", "Amazon shows a different ISBN than my printed copy.", Category.ISBN_METADATA, Priority.HIGH),
        ("Bad copies", "The print quality is terrible, images are blurry.", Category.PRINTING_QUALITY, Priority.HIGH),
        ("Unavailable", "My book shows Currently Unavailable on Amazon.", Category.DISTRIBUTION, Priority.HIGH),
        ("Bio", "Can I update my author bio please?", Category.GENERAL, Priority.LOW),
    ],
)
def test_fallback_classifies_brief_examples(subject, description, category, priority):
    result = fallback.classify(subject, description)
    assert (result.category, result.priority) == (category, priority)


def test_fallback_uses_production_status_for_books_in_production():
    result = fallback.classify("Question", "When can I see my book?", "In Production - Typesetting")
    assert result.category == Category.PRODUCTION_STATUS


def test_ai_output_accepts_labels_and_rejects_garbage():
    parsed = AIClassification.model_validate({"category": "Royalty & Payments", "priority": "high", "reason": "x"})
    assert (parsed.category, parsed.priority) == (Category.ROYALTY_PAYMENTS, Priority.HIGH)
    with pytest.raises(ValidationError):
        AIClassification.model_validate({"category": "Refunds", "priority": "HIGH"})


def test_kb_sends_only_relevant_sections():
    royalty = kb_for_category(Category.ROYALTY_PAYMENTS)
    assert "ROYALTY POLICY" in royalty and "PRINTING & QUALITY" not in royalty
    assert len(royalty) < len("\n\n".join(KB_SECTIONS.values())) / 2


def test_payout_schedule():
    assert next_payout(date(2026, 10, 7))["pay_by"] == date(2026, 11, 14)
    assert next_payout(date(2026, 11, 20))["pay_by"] == date(2027, 2, 14)


def test_book_facts_flag_threshold_and_overdue():
    book = {"title": "T", "isbn": "1", "genre": "G", "status": "Published & Live", "mrp": 300,
            "author_royalty_per_copy": 25, "total_copies_sold": 34, "total_royalty_earned": 850,
            "royalty_paid": 0, "royalty_pending": 850, "publication_date": "2024-11-05",
            "last_royalty_payout_date": None, "available_on": [], "print_partner": None}
    facts = "\n".join(drafter.book_facts(book, date(2026, 10, 7)))
    assert "below the ₹1,000 minimum payout threshold" in facts and "overdue" not in facts.lower().replace("not overdue", "")

    overdue = {**book, "royalty_pending": 3570, "last_royalty_payout_date": "2025-10-15"}
    assert "looks overdue" in "\n".join(drafter.book_facts(overdue, date(2026, 10, 7)))


def test_internal_notes_never_reach_the_draft_prompt():
    messages = [
        {"kind": "REPLY", "sender_role": "AUTHOR", "body": "Any update?"},
        {"kind": "NOTE", "sender_role": "ADMIN", "body": "SECRET: designer on leave"},
    ]
    assert "SECRET" not in drafter.conversation_text(messages)
