from __future__ import annotations

from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from ..config import ai_is_configured
from ..core.policies import get_source_weight
from ..llm.model_factory import get_chat_model
from ..models import Evidence


class ConflictResolutionPayload(BaseModel):
    resolved_value: str = Field(
        description="The value recommended to resolve the conflict"
    )
    reason: str = Field(
        description="Detailed logical explanation for why this source was selected over others"
    )
    confidence: float = Field(
        description="Confidence score from 0.0 to 1.0 representing selection certainty"
    )


class ConflictAgent:
    """LangChain Cross-Source Conflict Agent.

    Compares competing evidence across documents, ranks source reliability,
    and proposes a resolution with a detailed Chain of Thought explanation.
    """

    def run(
        self,
        field: str,
        candidates: list[dict[str, Any]],
        context: str,
    ) -> dict[str, Any]:
        """Evaluate competing values and return a resolution proposal."""
        if not candidates:
            return {
                "conflict": False,
                "recommended_value": None,
                "reason": "No candidates to evaluate.",
                "confidence": 1.0,
            }

        # 1. Determine if there is a real conflict (more than 1 unique normalized value)
        unique_vals = list({c["normalized_display"].strip().lower() for c in candidates if c.get("normalized_display")})
        if len(unique_vals) <= 1:
            # No real conflict
            first = candidates[0]
            return {
                "conflict": False,
                "recommended_value": first["raw_value"],
                "reason": "All sources and normalization forms agree on this value.",
                "confidence": 0.95,
            }

        # 2. Rank sources using our deterministic policy weights
        ranked_candidates = []
        for c in candidates:
            weight = get_source_weight(c["evidence"].method)
            ranked_candidates.append((weight, c))

        # Sort descending by source reliability weight
        ranked_candidates.sort(key=lambda item: item[0], reverse=True)
        highest_weight = ranked_candidates[0][0]
        contenders = [item for item in ranked_candidates if item[0] == highest_weight]

        # 3. LLM resolves the conflict if configured
        if ai_is_configured() and context:
            try:
                llm = get_chat_model(temperature=0.0)
                structured_llm = llm.with_structured_output(ConflictResolutionPayload)

                candidates_desc = "\n".join(
                    f"- Value: {c['raw_value']} (Normalized: {c.get('normalized_display')}), Method: {c['evidence'].method}, Snippet: “{c['evidence'].snippet}”"
                    for _, c in ranked_candidates
                )

                prompt = ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            (
                                "You are a cautious industrial catalog conflict auditor.\n"
                                "Your job is to resolve a conflict on product attribute '{field}'.\n"
                                "Compare the source snippets, evaluate their reliability weights, and consult the document context.\n"
                                "Explain why you recommended one choice over another."
                            ),
                        ),
                        (
                            "user",
                            (
                                "Attribute: {field}\n"
                                "Competing candidates:\n{candidates_desc}\n\n"
                                "Document Context:\n---\n{context}\n---"
                            ),
                        ),
                    ]
                )

                chain = prompt | structured_llm
                result: ConflictResolutionPayload = chain.invoke(
                    {
                        "field": field,
                        "candidates_desc": candidates_desc,
                        "context": context[:10000],
                    }
                )

                return {
                    "conflict": True,
                    "recommended_value": result.resolved_value,
                    "reason": f"Conflict Agent recommendation: {result.reason}",
                    "confidence": result.confidence,
                }
            except Exception:
                pass

        # 4. Deterministic policy fallback: select highest source quality contender
        if len(contenders) == 1:
            resolved = contenders[0][1]
            return {
                "conflict": True,
                "recommended_value": resolved["raw_value"],
                "reason": (
                    f"Resolved via deterministic Policy: Source kind '{resolved['evidence'].method}' "
                    f"(weight {highest_weight}) is more authoritative than competing alternatives."
                ),
                "confidence": 0.80,
            }

        # Tie among equal quality sources
        first_contender = contenders[0][1]
        other_contender = contenders[1][1]
        return {
            "conflict": True,
            "recommended_value": first_contender["raw_value"],
            "reason": (
                f"Tie alert: Source reliability is equal for competing values "
                f"('{first_contender['raw_value']}' vs '{other_contender['raw_value']}'). "
                f"Flagged for human reviewer review."
            ),
            "confidence": 0.40,
        }
