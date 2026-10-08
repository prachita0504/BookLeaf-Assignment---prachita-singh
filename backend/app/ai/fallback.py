"""Keyword-based classifier used instantly on ticket creation and whenever the AI is unavailable.

Its job is a *safe default*, not accuracy: every ticket gets a sensible category and priority in
under a millisecond and at zero cost, so the queue is never blocked by the LLM. The AI then
refines it in the background.
"""

import re
from dataclasses import dataclass

from app.schemas.common import Category, Priority

_CATEGORY_KEYWORDS: dict[Category, list[str]] = {
    Category.ROYALTY_PAYMENTS: [
        "royalt", "payment", "paid", "payout", "pay me", "bank", "money", "earning", "amount",
        "₹", "inr", "transfer", "statement", "invoice", "tds", "commission",
    ],
    Category.ISBN_METADATA: [
        "isbn", "metadata", "barcode", "imprint", "wrong title", "wrong author", "author name",
        "misspel", "spelling", "description", "blurb", "category on amazon", "duplicate",
    ],
    Category.PRINTING_QUALITY: [
        "print quality", "printing", "misprint", "blurry", "blurred", "faded", "binding", "pages",
        "misaligned", "torn", "damaged", "defect", "colour", "color", "ink", "cover quality", "author copies",
    ],
    Category.DISTRIBUTION: [
        "unavailable", "not available", "out of stock", "amazon", "flipkart", "listing", "listed",
        "can't find", "cannot find", "not showing", "buy link", "store", "delivery", "shipping",
    ],
    Category.PRODUCTION_STATUS: [
        "typesetting", "cover design", "proofread", "proof", "editing", "manuscript", "production",
        "when will", "how long", "status", "delay", "still in", "stage", "publish date", "launch",
    ],
    Category.GENERAL: [
        "can i", "how do i", "how can i", "update my", "change my", "bio", "package", "contract",
        "account", "password", "email address", "bestseller breakthrough", "marketing",
    ],
}

_CRITICAL_PATTERNS = [
    r"\b(legal|lawyer|court|fraud|scam|police|consumer forum)\b",
    r"\b([6-9]|1[0-2]|six|seven|eight|nine|ten|twelve)\s+months?\b.*\b(royalt|paid|payment|payout)",
    r"\b(royalt|paid|payment|payout).*\b([6-9]|1[0-2]|six|seven|eight|nine|ten|twelve)\s+months?\b",
    r"\b(never|not)\s+(been\s+)?(received|paid)\b.*\b(any|single)\b",
]
_HIGH_PATTERNS = [
    r"\bisbn\b.*\b(wrong|different|duplicate|mismatch|incorrect|error)\b",
    r"\b(wrong|different|duplicate|mismatch|incorrect)\b.*\bisbn\b",
    r"\b(not|haven't|have not|never)\s+(been\s+)?(received|paid)\b",
    r"\b(overdue|unacceptable|urgent|asap|immediately|terrible|furious|disappointed)\b",
    r"\b(misprint|blurry|misaligned|defect|damaged|torn)\b",
    r"\b(unavailable|out of stock|not available)\b",
]
_LOW_PATTERNS = [
    r"\b(author bio|my bio|profile|photo|update (my|the) (bio|description|details))\b",
    r"^(can|could|how do|how can|is it possible)\b",
    r"\b(just wondering|quick question|curious)\b",
]


@dataclass(frozen=True)
class RuleClassification:
    category: Category
    priority: Priority
    reason: str


def classify(subject: str, description: str, book_status: str | None = None) -> RuleClassification:
    text = f"{subject}\n{description}".lower()

    scores = {cat: sum(1 for kw in kws if kw in text) for cat, kws in _CATEGORY_KEYWORDS.items()}
    # Questions about a book still in production are almost always status questions.
    if book_status and book_status.startswith("In Production"):
        scores[Category.PRODUCTION_STATUS] += 2
    category, best = max(scores.items(), key=lambda kv: kv[1])
    if best == 0:
        category = Category.GENERAL

    if any(re.search(p, text) for p in _CRITICAL_PATTERNS):
        priority = Priority.CRITICAL
    elif any(re.search(p, text) for p in _HIGH_PATTERNS) or category == Category.ISBN_METADATA and "isbn" in text:
        priority = Priority.HIGH
    elif any(re.search(p, text, re.MULTILINE) for p in _LOW_PATTERNS) and category in (
        Category.GENERAL,
        Category.ISBN_METADATA,
    ):
        priority = Priority.LOW
    else:
        priority = Priority.MEDIUM

    matched = [kw for kw in _CATEGORY_KEYWORDS.get(category, []) if kw in text][:4]
    reason = f"Keyword rules matched: {', '.join(matched)}" if matched else "No strong keywords; default triage"
    return RuleClassification(category, priority, reason)
