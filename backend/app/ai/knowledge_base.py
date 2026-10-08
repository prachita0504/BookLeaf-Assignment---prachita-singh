"""BookLeaf Knowledge Base split into sections + tone guide + calibration examples.

Cost note: the full KB is roughly 1,100 tokens. A royalty ticket only needs the royalty policy, the
tone guide and one or two calibration examples, so `kb_for_category()` sends only the relevant
sections instead of the whole KB on every call.
"""

from app.schemas.common import Category

KB_SECTIONS: dict[str, str] = {
    "company": """COMPANY
- BookLeaf Publishing is a self-publishing company operating in India and the US.
- Packages: Standard Free (no upfront cost) and Bestseller Breakthrough (premium, paid, with marketing and distribution add-ons).
- BookLeaf handles cover design, typesetting, ISBN assignment, printing, distribution and royalty management.
- In-house printing facility and warehouse in Delhi; print partners: Repro India and Epitome Books.""",
    "royalty": """ROYALTY POLICY
- 80/20 split: 80% of the net profit per book goes to the author, 20% to BookLeaf.
- Net profit = MRP minus printing cost, platform commission (Amazon/Flipkart) and shipping charges.
- Royalties are calculated quarterly and paid within 45 days of the quarter ending.
- Minimum payout threshold: ₹1,000. Below that, royalties roll over to the next quarter.
- Payouts are made by bank transfer to the account linked in the author's dashboard.
- Authors can see a detailed royalty breakdown (sales per platform) in their dashboard.""",
    "isbn": """ISBN POLICY
- Every BookLeaf book gets a unique ISBN assigned by BookLeaf, registered under BookLeaf's publisher imprint.
- An ISBN under the author's own imprint must be obtained by the author independently.
- ISBN errors (duplicate ISBN, wrong book linked) are HIGH PRIORITY and escalated to the production team; resolution within 48 hours.""",
    "printing": """PRINTING & QUALITY
- In-house printing handles most orders; overflow or special formats go to Repro India or Epitome Books.
- Standard print turnaround: 5–7 business days from order confirmation.
- Quality issues (misprints, binding defects, colour inconsistency): BookLeaf arranges a FREE reprint after verification. The author may need to share photos of the defective copy. Reprint timeline: 5–7 business days.""",
    "distribution": """DISTRIBUTION & AVAILABILITY
- Books are listed on Amazon India, Flipkart, Amazon US, Amazon UK and the BookLeaf Store.
- New listings typically go live within 7–10 business days after publication is complete.
- "Unavailable" on a platform usually means a stock sync issue; BookLeaf's team can trigger a re-sync and the listing is live again within 24–48 hours.""",
    "production": """PRODUCTION STAGES
- Manuscript Received → Editing (if opted) → Cover Design → Typesetting → Proofreading → ISBN Assignment → Printing → Distribution Setup → Published & Live.
- Authors are emailed at each stage. Delays usually happen at Cover Design (waiting for author approval) and Proofreading (revision rounds).""",
    "metadata": """METADATA UPDATES
- Book metadata (e.g. description) can be updated after going live: submit through the dashboard or email the BookLeaf team.
- Changes typically reflect on platforms within 3–5 business days.""",
}

TONE_GUIDE = """BOOKLEAF COMMUNICATION STYLE
- Empathetic and professional. Authors are partners, not customers to be managed.
- Acknowledge the author's concern BEFORE jumping to solutions.
- Be specific: use the actual numbers, dates and statuses from the account data, not vague reassurance.
- If something is BookLeaf's fault (delayed royalties, ISBN error), own it directly. No corporate deflection.
- If escalation or investigation is needed, give a clear timeline (e.g. "within 48 hours"), never open-ended promises.
- Never blame the author, even if a delay is on their side; frame it collaboratively.
- Always end with a clear next step for the author and/or the BookLeaf team."""

# Calibration examples taken from BookLeaf's guidelines: what a good answer *does*.
EXAMPLES: dict[Category, list[tuple[str, str]]] = {
    Category.ROYALTY_PAYMENTS: [
        (
            "I published my book 4 months ago and still haven't received any royalty. What's going on?",
            "Acknowledge the frustration. Explain the quarterly cycle and 45-day payout window. Ask them to confirm "
            "their bank details are linked. Give the specific next payout date. If genuinely overdue, escalate with "
            "a 48-hour resolution timeline.",
        ),
        (
            "My royalty amount seems too low. I sold 200 copies but only received ₹3,000.",
            "Explain net profit = MRP minus printing, platform commission and shipping. Offer a detailed "
            "line-by-line royalty breakdown. Don't be defensive; offer transparency.",
        ),
    ],
    Category.ISBN_METADATA: [
        (
            "My book is showing a different ISBN on Amazon than what's on the physical copy.",
            "Treat as high priority. Acknowledge it's a serious data issue. Confirm escalation to the production "
            "team immediately. Give a 48-hour resolution timeline.",
        )
    ],
    Category.PRINTING_QUALITY: [
        (
            "I received my author copies and the print quality is terrible. The images are blurry and pages are misaligned.",
            "Apologise sincerely. Ask for photos of the defective copies. Confirm BookLeaf will arrange a free "
            "reprint once verified, with a 5–7 business day timeline.",
        )
    ],
    Category.DISTRIBUTION: [
        (
            "My book is published but it's showing as 'Currently Unavailable' on Amazon.",
            "Explain it's typically a stock sync issue. Confirm you're triggering a re-sync with the distribution "
            "team. Set the expectation: 24–48 hours.",
        )
    ],
    Category.PRODUCTION_STATUS: [
        (
            "It's been 3 weeks and my book is still in typesetting. When will it be done?",
            "Use the actual production status. If delayed, be honest about why (e.g. waiting on proof approval). "
            "Give a specific updated timeline. Frame it collaboratively and never blame the author.",
        )
    ],
    Category.GENERAL: [
        (
            "Can I update the description of my book on Amazon after it's already live?",
            "Yes: metadata updates can be submitted through the dashboard or by emailing the BookLeaf team; "
            "changes reflect on platforms within 3–5 business days.",
        )
    ],
}

_SECTIONS_BY_CATEGORY: dict[Category, list[str]] = {
    Category.ROYALTY_PAYMENTS: ["royalty"],
    Category.ISBN_METADATA: ["isbn", "metadata"],
    Category.PRINTING_QUALITY: ["printing"],
    Category.DISTRIBUTION: ["distribution"],
    Category.PRODUCTION_STATUS: ["production", "distribution"],
    # General questions can touch anything, so they get the compact overview + the most asked-about policies.
    Category.GENERAL: ["company", "metadata", "royalty"],
}


def kb_for_category(category: Category) -> str:
    return "\n\n".join(KB_SECTIONS[key] for key in _SECTIONS_BY_CATEGORY[category])


def examples_for_category(category: Category) -> str:
    return "\n\n".join(
        f'Author: "{query}"\nA good reply: {guidance}' for query, guidance in EXAMPLES[category]
    )
