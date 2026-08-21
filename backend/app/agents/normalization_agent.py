from __future__ import annotations

from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from ..config import ai_is_configured
from ..llm.model_factory import get_chat_model
from ..normalization import normalize_value


class NormalizationDecision(BaseModel):
    value: str = Field(
        description="The canonical normalized value (e.g., 'Stainless Steel 304' or numeric representation)"
    )
    unit: str | None = Field(
        default=None,
        description="The standardized unit of measurement (e.g., 'in', 'WOG', '°C')",
    )
    display: str = Field(
        description="The PIM-ready user-friendly display string (e.g. '1 in', '600 WOG', 'SS304')"
    )
    reason: str = Field(description="The rationale behind the normalization mapping")


class NormalizationAgent:
    """LangChain Normalization Agent.

    Employs local deterministic rules (Pint, lookup tables) and falls back
    to LLM reasoning for complex/unrecognized raw strings.
    """

    def run(self, field: str, raw_value: str, historical_corrections: list[dict] = None) -> dict[str, Any]:
        """Run the hybrid normalization pipeline on a raw value."""
        if not raw_value or not raw_value.strip():
            return {
                "value": None,
                "unit": None,
                "display": None,
                "explanation": "No value provided.",
                "confidence": 0.0,
            }

        # 0. Check historical corrections (Feedback/Learning loop)
        if historical_corrections:
            for corr in historical_corrections:
                if corr.get("field") == field and corr.get("raw_value") and str(corr.get("raw_value")).strip().lower() == raw_value.strip().lower():
                    val = corr.get("reviewed_value")
                    return {
                        "value": val,
                        "unit": None,
                        "display": val,
                        "explanation": "Learned from past human review correction.",
                        "confidence": 0.98,
                    }

        # 1. Try deterministic rules first
        normalized, explanation = normalize_value(field, raw_value)

        # We treat it as a confident match if we found a standard mapping
        # and didn't fall back to "Unrecognized..." or parse failure warnings
        if normalized and normalized.value is not None:
            if not explanation or ("unrecognized" not in explanation.lower() and "could not parse" not in explanation.lower()):
                return {
                    "value": normalized.value,
                    "unit": normalized.unit,
                    "display": normalized.display,
                    "explanation": explanation or "Normalized using local deterministic rules.",
                    "confidence": 0.95,
                }

        # 2. Fall back to LLM reasoning if configured
        if ai_is_configured():
            try:
                llm = get_chat_model(temperature=0.0)
                structured_llm = llm.with_structured_output(NormalizationDecision)

                prompt = ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            (
                                "You are a cautious industrial Valve & Fitting normalization agent.\n"
                                "Normalize the raw value for the field '{field}' to canonical specifications.\n"
                                "Ensure standard formatting: metric sizes convert to inches, materials map to full names (e.g., SS316 -> Stainless Steel 316), and temperatures standardise to Celsius.\n"
                                "Provide canonical unit and display string."
                            ),
                        ),
                        ("user", "Raw value to normalize: '{raw_value}'"),
                    ]
                )

                chain = prompt | structured_llm
                result: NormalizationDecision = chain.invoke(
                    {"field": field, "raw_value": raw_value}
                )

                # Attempt to parse numeric values if appropriate
                parsed_val: Any = result.value
                try:
                    if result.value.replace(".", "", 1).isdigit():
                        parsed_val = float(result.value)
                        if parsed_val.is_integer():
                            parsed_val = int(parsed_val)
                except Exception:
                    pass

                return {
                    "value": parsed_val,
                    "unit": result.unit,
                    "display": result.display,
                    "explanation": f"LLM Normalization: {result.reason}",
                    "confidence": 0.85,
                }
            except Exception:
                pass

        # 3. Ultimate Fallback (retains raw value)
        return {
            "value": raw_value,
            "unit": None,
            "display": raw_value,
            "explanation": explanation or "Retained raw value (unrecognized).",
            "confidence": 0.50,
        }
