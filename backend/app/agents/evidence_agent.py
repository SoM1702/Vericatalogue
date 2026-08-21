from __future__ import annotations

import re
from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from ..config import ai_is_configured
from ..extraction import (
    CONNECTION_PATTERN,
    MATERIAL_PATTERN,
    PRESSURE_PATTERN,
    SIZE_PATTERN,
    TEMPERATURE_PATTERN,
)
from ..llm.model_factory import get_chat_model


class EvidenceExtraction(BaseModel):
    value: str = Field(
        description="The raw attribute value found in the text (e.g. '600 WOG', 'SS304')"
    )
    snippet: str = Field(
        description="The exact verbatim quote from the context that supports this value"
    )
    page: int | None = Field(
        default=None,
        description="The page number where the quote is located, if identifiable from headers",
    )
    row: int | None = Field(
        default=None,
        description="The table row number where the quote is located, if from a structured table",
    )


class EvidenceAgent:
    """LangChain Evidence Agent.

    Locates verbatim source quotes and extracts raw values for a specific PIM field.
    """

    def run(self, field: str, context: str, filename: str) -> dict[str, Any] | None:
        """Run the Evidence Agent over the context for a given PIM field."""
        if not context or not context.strip():
            return None

        if ai_is_configured():
            try:
                llm = get_chat_model(temperature=0.0)
                structured_llm = llm.with_structured_output(EvidenceExtraction)

                prompt = ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            (
                                "You are a cautious industrial-catalog evidence retrieval agent.\n"
                                "Your task is to locate the raw value and the exact verbatim snippet for the product attribute '{field}'.\n"
                                "Only extract information that is explicitly stated in the context.\n"
                                "If the attribute is not explicitly present, return empty strings."
                            ),
                        ),
                        ("user", "Source document context:\n---\n{context}\n---"),
                    ]
                )

                chain = prompt | structured_llm
                result: EvidenceExtraction = chain.invoke(
                    {"field": field, "context": context[:10000]}
                )

                if result.value and result.value.strip() and result.snippet.strip():
                    val = result.value.strip()
                    snip = result.snippet.strip()

                    # Verbatim grounding verification
                    if val.lower() in context.lower() and snip.lower() in context.lower():
                        return {
                            "value": val,
                            "snippet": snip,
                            "source_file": filename,
                            "page": result.page,
                            "row": result.row,
                            "evidence_type": "direct",
                            "confidence": 0.95,
                        }
            except Exception:
                pass

        # Fallback to local deterministic regex-based extraction
        return self._run_deterministic_fallback(field, context, filename)

    @staticmethod
    def _run_deterministic_fallback(
        field: str, context: str, filename: str
    ) -> dict[str, Any] | None:
        patterns = {
            "material": MATERIAL_PATTERN,
            "size": SIZE_PATTERN,
            "end_connection": CONNECTION_PATTERN,
            "pressure_rating": PRESSURE_PATTERN,
            "temperature_range": TEMPERATURE_PATTERN,
        }

        pattern = patterns.get(field)
        if not pattern:
            return None

        # Scan line by line for explicit labels or keyword matching
        lines = [line.strip() for line in context.splitlines() if line.strip()]
        for line in lines:
            match = pattern.search(line)
            if match:
                val = match.group(0)
                return {
                    "value": val,
                    "snippet": line,
                    "source_file": filename,
                    "page": 1,
                    "row": None,
                    "evidence_type": "direct",
                    "confidence": 0.90,
                }
        return None
