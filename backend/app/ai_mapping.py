from __future__ import annotations

import asyncio
import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import AI_API_KEY, AI_BASE_URL, AI_BATCH_LIMIT, AI_MODEL, AI_TIMEOUT_SECONDS, ai_is_configured
from .extraction import FIELD_ORDER, Candidate, SourceRow
from .models import Evidence


SYSTEM_PROMPT = """You are a cautious industrial-catalog attribute candidate mapper.
Return JSON only in this shape: {"attributes":[{"field":"allowed_field","raw_value":"exact source value","source_quote":"exact short quote from source"}]}.
Allowed fields: manufacturer, manufacturer_part_number, product_title, product_type, material, size, end_connection, pressure_rating, temperature_range, certifications, description.
Only return a field when both raw_value and source_quote occur verbatim in the supplied source text. Never create facts, calculate values, resolve disagreements, or return explanations. Omit uncertain fields."""


class AIMapperError(RuntimeError):
    pass


def _compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def attach_grounded_candidates(source: SourceRow, response: dict[str, Any]) -> int:
    """Attach only AI candidates that quote text actually present in this source.

    They stay `inferred=True`, so the model never upgrades a field to Verified by itself.
    """
    source_text = _compact(source.context)
    raw_attributes = response.get("attributes", [])
    if not isinstance(raw_attributes, list) or not source_text:
        return 0
    attached = 0
    for item in raw_attributes:
        if not isinstance(item, dict):
            continue
        field = item.get("field")
        raw_value = item.get("raw_value")
        source_quote = item.get("source_quote")
        if field not in FIELD_ORDER or not all(isinstance(value, str) and value.strip() for value in (raw_value, source_quote)):
            continue
        compact_value = _compact(raw_value)
        compact_quote = _compact(source_quote)
        if compact_value not in source_text or compact_quote not in source_text or compact_value not in compact_quote:
            continue
        existing_values = {_compact(candidate.raw_value) for candidate in source.candidates.get(field, [])}
        if compact_value in existing_values:
            continue
        source.candidates.setdefault(field, []).append(
            Candidate(
                raw_value.strip(),
                Evidence(
                    source_file=source.source_file,
                    snippet=source_quote.strip()[:500],
                    method="optional_ai_candidate_mapping",
                ),
                inferred=True,
            )
        )
        attached += 1
    return attached


def _parse_model_content(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", stripped, flags=re.I)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise AIMapperError("The configured AI provider returned non-JSON candidate data.") from exc
    if not isinstance(parsed, dict):
        raise AIMapperError("The configured AI provider returned an unexpected candidate structure.")
    return parsed


def _request_candidates(source_text: str) -> dict[str, Any]:
    payload = json.dumps(
        {
            "model": AI_MODEL,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Source text follows:\n---\n{source_text[:12000]}\n---"},
            ],
        }
    ).encode("utf-8")
    request = Request(
        AI_BASE_URL,
        data=payload,
        headers={"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=AI_TIMEOUT_SECONDS) as response:  # noqa: S310 - endpoint is user-configured.
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise AIMapperError(f"The AI provider rejected the candidate-mapping request ({exc.code}).") from exc
    except (URLError, TimeoutError) as exc:
        raise AIMapperError("The AI provider could not be reached. Deterministic extraction still completed.") from exc
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIMapperError("The AI provider response did not contain a chat-completion message.") from exc
    if not isinstance(content, str):
        raise AIMapperError("The AI provider response was not text.")
    return _parse_model_content(content)


async def enrich_with_ai_candidates(sources: list[SourceRow], batch: bool = False) -> int:
    if not ai_is_configured():
        return 0
    selected_sources = sources[:AI_BATCH_LIMIT] if batch else sources
    attached = 0
    for source in selected_sources:
        if not source.context:
            continue
        response = await asyncio.to_thread(_request_candidates, source.context)
        attached += attach_grounded_candidates(source, response)
    return attached


def ai_status() -> dict[str, Any]:
    configured = ai_is_configured()
    return {
        "enabled": configured,
        "configured": configured,
        "model": AI_MODEL if configured else None,
        "mode": "grounded_candidate_mapping" if configured else "deterministic_only",
        "message": (
            "Optional AI candidate mapping is active. Candidates stay Inferred until reviewed."
            if configured
            else "Optional AI candidate mapping is off. Deterministic evidence extraction is active."
        ),
    }
