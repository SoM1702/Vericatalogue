import os
from ..models import ProductAttribute, ProductRecord

# Configurable Verification Confidence Threshold
CONFIDENCE_THRESHOLD = float(os.getenv("VERICATALOG_CONFIDENCE_THRESHOLD", "0.90"))

# Source quality/reliability weights
SOURCE_WEIGHTS = {
    # Direct manufacturer documents (technical datasheets / catalogs)
    "pdf_table_row_extraction": 5,
    "pdf_text_extraction": 5,
    "pdf_ocr_extraction": 4,
    # LLM and manual entry
    "agent_extraction_node": 3,
    "optional_ai_candidate_mapping": 3,
    "csv_row_extraction": 2,
    "manual_input": 2,
    # Layout-level inferences
    "pdf_layout_inference": 0,
    "deterministic_title_inference": 0,
    "test": 1,
}


def get_source_weight(method: str) -> int:
    """Return the reliability weight of a given evidence extraction method."""
    return SOURCE_WEIGHTS.get(method.strip().lower(), 1)


class PolicyEngine:
    """Deterministic validation and verification policy gateway.

    Decides if an attribute recommendation from the agents can be
    automatically verified and written to the PIM catalog DB,
    or if it must escalate to human review.
    """

    @staticmethod
    def evaluate(attribute: ProductAttribute) -> tuple[str, str]:
        """Evaluate an attribute against deterministic business policies.

        Returns a tuple: (Decision, Reason explanation).
        """
        # 1. Direct Evidence Check
        if not attribute.evidence:
            return "HUMAN_REVIEW", "Missing evidence: The attribute has no source context snippets."

        max_reliability = max(get_source_weight(ev.method) for ev in attribute.evidence)
        if max_reliability < 2:
            return (
                "HUMAN_REVIEW",
                f"Low source quality: Maximum evidence reliability is {max_reliability} (inference level). Direct source documentation required.",
            )

        # 2. Validation Checks
        failed_validations = [val for val in attribute.validation_results if val.status == "fail"]
        if failed_validations:
            fail_rules = ", ".join(val.rule.replace("_", " ") for val in failed_validations)
            return (
                "HUMAN_REVIEW",
                f"Validation failures: The attribute triggered failed rule checks ({fail_rules}).",
            )

        # 3. Conflict Check
        if attribute.status == "conflict":
            return "HUMAN_REVIEW", "Unresolved conflict: Sources disagree or competing candidates exist."

        # 4. Confidence Threshold Check
        if attribute.confidence < CONFIDENCE_THRESHOLD:
            return (
                "HUMAN_REVIEW",
                f"Low confidence: Score of {attribute.confidence:.2f} is below the verification threshold of {CONFIDENCE_THRESHOLD:.2f}.",
            )

        # Passes all gates
        return "AUTO_VERIFY", "Policy check passed: Attribute meets all direct evidence, quality, validation, and confidence criteria."
