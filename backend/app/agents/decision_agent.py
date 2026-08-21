from __future__ import annotations

from typing import Any, Literal
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from ..config import ai_is_configured
from ..core.policies import CONFIDENCE_THRESHOLD, get_source_weight
from ..llm.model_factory import get_chat_model


class DecisionResponse(BaseModel):
    decision: Literal[
        "AUTO_VERIFY",
        "AUTO_REJECT",
        "INFERRED",
        "MISSING",
        "CONFLICT",
        "HUMAN_REVIEW",
    ] = Field(description="The recommended workflow decision suggestion")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="The confidence score calculated from 0.0 to 1.0",
    )
    reason: str = Field(description="Structured explanation for the decision")


class DecisionAgent:
    """LangChain Decision Agent.

    Evaluates evidence, normalization, validations, and conflicts,
    computes an evidence-based confidence score, and suggests routing.
    """

    def run(self, field: str, attr_data: dict[str, Any]) -> dict[str, Any]:
        """Synthesize field status and recommend a verification routing."""
        # 1. Compute evidence-based confidence formula components
        evidence_strength = (
            1.0
            if any(ev.get("evidence_type", "direct") == "direct" for ev in attr_data.get("evidence", []))
            else 0.5
        )

        max_weight = 1
        if attr_data.get("evidence"):
            max_weight = max(get_source_weight(ev.get("method", "")) for ev in attr_data["evidence"])
        source_quality = min(max_weight / 5.0, 1.0)

        total_rules = len(attr_data.get("validation_results", []))
        passed_rules = sum(
            1 for val in attr_data.get("validation_results", []) if val.get("status") == "pass"
        )
        validation_score = passed_rules / total_rules if total_rules > 0 else 1.0

        consistency_score = 0.5 if attr_data.get("status") == "conflict" else 1.0

        # Overall confidence score formula
        confidence = float(
            evidence_strength * source_quality * validation_score * consistency_score
        )

        # 2. Query LLM for autonomous decision if configured
        if ai_is_configured():
            try:
                llm = get_chat_model(temperature=0.0)
                structured_llm = llm.with_structured_output(DecisionResponse)

                prompt = ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            (
                                "You are a cautious industrial catalog quality control manager.\n"
                                "You will review the data extraction audit facts for field '{field}' and recommend the workflow decision:\n"
                                "- AUTO_VERIFY: perfect direct evidence, passed validation, no conflicts, high confidence.\n"
                                "- AUTO_REJECT: definitely false/malformed values.\n"
                                "- CONFLICT: competing values exist.\n"
                                "- MISSING: mandatory data is missing.\n"
                                "- HUMAN_REVIEW: any warning, failed checks, low confidence, or ambiguity.\n"
                                "Do not verify if information is missing or ungrounded."
                            ),
                        ),
                        (
                            "user",
                            (
                                "Attribute: {field}\n"
                                "Facts:\n"
                                "- Raw Value: {raw_value}\n"
                                "- Normalized Display: {norm_display}\n"
                                "- Status: {status}\n"
                                "- Evidence-based Confidence Score: {confidence:.2f}\n"
                                "- Validation Failures: {failures_count}\n"
                                "- Disagreements: {has_conflict}"
                            ),
                        ),
                    ]
                )

                failures = sum(
                    1 for v in attr_data.get("validation_results", []) if v.get("status") == "fail"
                )
                result: DecisionResponse = (
                    prompt | structured_llm
                ).invoke(
                    {
                        "field": field,
                        "raw_value": attr_data.get("raw_value"),
                        "norm_display": attr_data.get("normalized_display"),
                        "status": attr_data.get("status"),
                        "confidence": confidence,
                        "failures_count": failures,
                        "has_conflict": "yes" if attr_data.get("status") == "conflict" else "no",
                    }
                )

                return {
                    "decision": result.decision,
                    "confidence": min(confidence, result.confidence),
                    "reason": f"Decision Agent routing: {result.reason}",
                }
            except Exception:
                pass

        # 3. Deterministic decision fallback
        if attr_data.get("status") == "conflict":
            decision = "CONFLICT"
            reason = "Escalated to CONFLICT due to competing source documentation."
        elif attr_data.get("status") == "missing":
            decision = "MISSING"
            reason = "No source evidence located."
        elif any(v.get("status") == "fail" for v in attr_data.get("validation_results", [])):
            decision = "HUMAN_REVIEW"
            reason = "Escalated to HUMAN_REVIEW due to failed deterministic validation rules."
        elif confidence >= CONFIDENCE_THRESHOLD:
            decision = "AUTO_VERIFY"
            reason = (
                f"Autonomous recommendation: High confidence ({confidence:.2f} >= threshold {CONFIDENCE_THRESHOLD:.2f}) "
                f"with valid direct evidence and no validation checks failing."
            )
        else:
            decision = "HUMAN_REVIEW"
            reason = f"Escalated to HUMAN_REVIEW: Confidence ({confidence:.2f}) is below verification threshold."

        return {
            "decision": decision,
            "confidence": confidence,
            "reason": reason,
        }
