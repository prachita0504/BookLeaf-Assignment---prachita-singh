"""Thin wrapper around the Groq API: timeouts, one retry on 429/5xx, usage logging.

Raises AIUnavailableError so callers can fall back instead of failing.

Resilience:
- `timeout` + `max_retries=1`: the Groq SDK retries once with backoff on 429, 5xx and timeouts.
- Rate-limit cool-down: after a 429 we stop calling Groq for the period it asks (Retry-After)
  instead of hammering it; callers fall back immediately during that window.
- Every call (success or failure) is logged with token usage and latency (ai_call_logs).
"""

import logging
import time

import groq

from app.core.config import get_settings
from app.core.exceptions import AIUnavailableError
from app.repositories import ai_log_repository

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_SECONDS = 30

_client: groq.AsyncGroq | None = None
_cooldown_until = 0.0


def _get_client() -> groq.AsyncGroq:
    global _client
    if _client is None:
        settings = get_settings()
        _client = groq.AsyncGroq(api_key=settings.groq_api_key, timeout=settings.groq_timeout_seconds, max_retries=1)
    return _client


async def complete(
    *,
    task: str,
    model: str,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float = 0.3,
    json_mode: bool = False,
    ticket_number: int | None = None,
) -> str:
    """Runs one chat completion and returns the text. Raises AIUnavailableError on any failure."""
    global _cooldown_until
    settings = get_settings()
    if not settings.ai_enabled:
        raise AIUnavailableError("AI is not configured (GROQ_API_KEY is empty)")
    if time.monotonic() < _cooldown_until:
        raise AIUnavailableError("AI is temporarily rate-limited; using fallback")

    kwargs: dict = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if model.startswith("openai/gpt-oss"):
        # Reasoning models spend hidden tokens "thinking". Low effort is plenty for support tasks
        # and keeps latency and cost down.
        kwargs["reasoning_effort"] = "low"

    started = time.monotonic()
    try:
        resp = await _get_client().chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            raise AIUnavailableError("AI returned an empty response")
    except groq.RateLimitError as exc:
        retry_after = _retry_after_seconds(exc)
        _cooldown_until = time.monotonic() + retry_after
        await _log(task, model, started, ticket_number, error=f"rate_limited (cool-down {retry_after}s)")
        raise AIUnavailableError("AI is rate-limited; please write the response manually") from exc
    except AIUnavailableError as exc:
        await _log(task, model, started, ticket_number, error=exc.message)
        raise
    except groq.APIError as exc:  # timeouts, connection errors, 5xx, bad request...
        await _log(task, model, started, ticket_number, error=f"{type(exc).__name__}: {str(exc)[:200]}")
        raise AIUnavailableError("AI service is unavailable right now") from exc

    usage = resp.usage
    await _log(
        task,
        model,
        started,
        ticket_number,
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
    )
    return text


def _retry_after_seconds(exc: groq.RateLimitError) -> int:
    try:
        return max(1, min(300, int(float(exc.response.headers.get("retry-after", DEFAULT_COOLDOWN_SECONDS)))))
    except (TypeError, ValueError, AttributeError):
        return DEFAULT_COOLDOWN_SECONDS


async def _log(task, model, started, ticket_number, *, error=None, prompt_tokens=0, completion_tokens=0):
    latency_ms = int((time.monotonic() - started) * 1000)
    if error:
        logger.warning("AI %s failed for ticket %s after %sms: %s", task, ticket_number, latency_ms, error)
    try:
        await ai_log_repository.log_call(
            task=task,
            model=model,
            success=error is None,
            ticket_number=ticket_number,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            error=error,
        )
    except Exception:  # logging must never break the main flow
        logger.exception("Failed to write AI call log")
