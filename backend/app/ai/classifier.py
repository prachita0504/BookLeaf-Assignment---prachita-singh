"""AI ticket classification: category + priority + short reason, validated against allowed values.

Uses the small/cheap model with JSON mode. The output is parsed and validated; anything malformed
raises AIUnavailableError, so the caller keeps the rule-based result instead of storing garbage.
"""

import json
import re

from pydantic import BaseModel, ValidationError, field_validator

from app.ai import client
from app.ai.prompts import CLASSIFY_SYSTEM, classify_user_message
from app.core.config import get_settings
from app.core.exceptions import AIUnavailableError
from app.schemas.common import CATEGORY_LABELS, Category, Priority

MAX_DESCRIPTION_CHARS = 1500  # long rants don't improve triage; they only cost tokens

# Accept the human label too ("Royalty & Payments"), in case the model echoes it.
_LABEL_TO_CATEGORY = {re.sub(r"[^a-z]", "", label.lower()): cat for cat, label in CATEGORY_LABELS.items()}


class AIClassification(BaseModel):
    category: Category
    priority: Priority
    reason: str = ""

    @field_validator("category", mode="before")
    @classmethod
    def normalise_category(cls, v):
        if isinstance(v, str):
            key = v.strip().upper().replace(" ", "_")
            if key in Category.__members__:
                return key
            return _LABEL_TO_CATEGORY.get(re.sub(r"[^a-z]", "", v.lower()), v)
        return v

    @field_validator("priority", mode="before")
    @classmethod
    def normalise_priority(cls, v):
        return v.strip().upper() if isinstance(v, str) else v

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, v: str) -> str:
        return v.strip()[:300]


async def classify(
    *, subject: str, description: str, book_line: str | None, ticket_number: int | None = None
) -> AIClassification:
    settings = get_settings()
    raw = await client.complete(
        task="CLASSIFY",
        model=settings.groq_classify_model,
        system=CLASSIFY_SYSTEM,
        user=classify_user_message(subject, description[:MAX_DESCRIPTION_CHARS], book_line),
        max_tokens=400,  # includes the reasoning model's hidden "thinking" tokens
        temperature=0,  # deterministic triage
        json_mode=True,
        ticket_number=ticket_number,
    )
    try:
        return AIClassification.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AIUnavailableError(f"AI returned an invalid classification: {raw[:120]}") from exc
