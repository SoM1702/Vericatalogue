from __future__ import annotations

import uuid

from .models import ProductAttribute, ProductRecord, ReviewAgentPlan, ReviewAgentTask, ReviewAgentToolTrace


# Kept local to avoid coupling the review controller back to CatalogService.
REQUIRED_FIELDS = {
    "manufacturer",
    "manufacturer_part_number",
    "product_type",
    "material",
    "size",
    "end_connection",
    "pressure_rating",
}


class EvidenceReviewAgent:
    """A bounded, local tool-using controller for human catalog review.

    This is deliberately not an autonomous decision-maker. It sequentially runs
    a small set of inspect-only tools and returns a prioritised human task list.
    The trace is persisted by the repository, so a reviewer can see exactly what
    the agent inspected. No AI provider, mutation, or external call is required.
    """

    def run(self, product: ProductRecord) -> ReviewAgentPlan:
        trace: list[ReviewAgentToolTrace] = []

        exceptions = self._identify_exceptions(product)
        trace.append(
            ReviewAgentToolTrace(
                tool="identify_exceptions",
                item_count=len(exceptions),
                outcome=(
                    f"Found {len(exceptions)} field(s) that are inferred, missing, conflicting, or failed validation."
                    if exceptions
                    else "No exception fields found."
                ),
            )
        )

        provenance = self._inspect_provenance(exceptions)
        trace.append(
            ReviewAgentToolTrace(
                tool="inspect_provenance",
                item_count=len(provenance),
                outcome=f"Checked retained source evidence for {len(provenance)} exception field(s).",
            )
        )

        validation_failures = self._evaluate_validation(exceptions)
        trace.append(
            ReviewAgentToolTrace(
                tool="evaluate_validation",
                item_count=len(validation_failures),
                outcome=(
                    f"Found failed validation on {len(validation_failures)} exception field(s)."
                    if validation_failures
                    else "No additional failed validation rules found."
                ),
            )
        )

        tasks = self._rank_human_actions(exceptions, validation_failures)
        trace.append(
            ReviewAgentToolTrace(
                tool="rank_human_actions",
                item_count=len(tasks),
                outcome=(
                    f"Ranked {len(tasks)} human review action(s); no product field was changed."
                    if tasks
                    else "No human action is required by the current deterministic checks."
                ),
            )
        )

        return ReviewAgentPlan(
            id=f"ra_{uuid.uuid4().hex[:12]}",
            product_id=product.id,
            tool_trace=trace,
            tasks=tasks,
            summary=(
                "The agent found no exception fields. Existing verified evidence remains available for spot review."
                if not tasks
                else f"The agent found {len(tasks)} review action(s), ordered by conflict, required-field risk, evidence coverage, and validation failures."
            ),
        )

    @staticmethod
    def _identify_exceptions(product: ProductRecord) -> list[ProductAttribute]:
        return [
            attribute
            for attribute in product.attributes
            if attribute.status in {"conflict", "missing", "inferred"}
            or any(result.status == "fail" for result in attribute.validation_results)
        ]

    @staticmethod
    def _inspect_provenance(attributes: list[ProductAttribute]) -> dict[str, int]:
        return {attribute.field: len(attribute.evidence) for attribute in attributes}

    @staticmethod
    def _evaluate_validation(attributes: list[ProductAttribute]) -> set[str]:
        return {
            attribute.field
            for attribute in attributes
            if any(result.status == "fail" for result in attribute.validation_results)
        }

    @staticmethod
    def _rank_human_actions(attributes: list[ProductAttribute], validation_failures: set[str]) -> list[ReviewAgentTask]:
        tasks: list[ReviewAgentTask] = []
        for attribute in attributes:
            priority = 0
            if attribute.status == "conflict":
                priority += 100
                action = "resolve_conflict"
                reason = "Competing normalized values are retained. Compare every source reference before choosing a reviewed value."
            elif attribute.status == "missing":
                priority += 80 if attribute.field in REQUIRED_FIELDS else 35
                action = "find_source_value"
                reason = (
                    "This required PIM field has no retained source value. Locate an authorised source or keep the gap explicit."
                    if attribute.field in REQUIRED_FIELDS
                    else "No direct source value is retained for this optional field. Do not invent a replacement."
                )
            else:
                priority += 55
                action = "verify_candidate"
                reason = "This is an inferred candidate. Confirm its retained source quote before approving it."

            if attribute.field in validation_failures:
                priority += 20
                reason += " A deterministic validation rule also failed; inspect its rule message before making the human decision."
            if attribute.review_status == "pending":
                priority += 5

            tasks.append(
                ReviewAgentTask(
                    field=attribute.field,
                    status=attribute.status,
                    review_status=attribute.review_status,
                    priority=priority,
                    recommended_action=action,
                    reason=reason,
                    evidence_count=len(attribute.evidence),
                )
            )
        return sorted(tasks, key=lambda task: (-task.priority, task.field))
