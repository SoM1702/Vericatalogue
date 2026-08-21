from __future__ import annotations

from typing import Any, Literal
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from ..config import ai_is_configured
from ..llm.model_factory import get_chat_model
from ..models import NormalizedValue, ValidationResult



class ValidationExplanation(BaseModel):
    summary: str = Field(
        description="A concise summary of why the validation rule failed or succeeded"
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        description="The PIM risk level of the validation warning"
    )


class ValidationAgent:
    """LangChain Validation Agent.

    Wraps local deterministic validation rules and uses LLM reasoning to
    interpret failures or domain issues.
    """

    def run(
        self,
        field: str,
        normalized: NormalizedValue | None,
        raw_value: str,
        attributes_dict: dict[str, Any],
    ) -> list[ValidationResult]:
        """Run validation rules for an attribute."""
        # 1. Run deterministic validations first
        from ..service import CatalogService
        # Reconstruct candidates structure for the service helper
        candidates_by_field = {
            f: [
                type(
                    "MockCandidate",
                    (),
                    {"raw_value": attr.raw_value or ""},
                )
            ]
            for f, attr in attributes_dict.items()
            if attr.raw_value
        }

        # Call CatalogService's static validation helper
        validations = CatalogService._validation_for_value(
            field, normalized, raw_value, candidates_by_field
        )

        failed_rules = [val for val in validations if val.status == "fail"]

        # 2. LLM reasons about validation failures if configured
        if failed_rules and ai_is_configured():
            try:
                llm = get_chat_model(temperature=0.0)
                structured_llm = llm.with_structured_output(ValidationExplanation)

                prompt = ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            (
                                "You are a cautious industrial safety auditor.\n"
                                "Explain the validation rule failures for field '{field}' in a valve/fitting catalog.\n"
                                "Identify risks associated with: incorrect sizing, materials mismatch, or high pressure class ratings.\n"
                                "Keep your summary concise."
                            ),
                        ),
                        (
                            "user",
                            (
                                "Raw Value: '{raw_value}'\n"
                                "Normalized Value: '{norm_val}'\n"
                                "Failing Rule: '{rule_name}'\n"
                                "Rule Message: '{rule_msg}'"
                            ),
                        ),
                    ]
                )

                for val in failed_rules:
                    result: ValidationExplanation = (
                        prompt | structured_llm
                    ).invoke(
                        {
                            "field": field,
                            "raw_value": raw_value,
                            "norm_val": normalized.display if normalized else "None",
                            "rule_name": val.rule,
                            "rule_msg": val.message,
                        }
                    )
                    # Update message with LLM reasoning
                    val.message = f"{val.message} (Audit warning: {result.summary})"
            except Exception:
                pass

        return validations
