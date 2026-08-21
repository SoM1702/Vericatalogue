from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


FieldStatus = Literal["verified", "inferred", "missing", "conflict"]
ReviewStatus = Literal["pending", "approved", "rejected", "edited"]
ValidationStatus = Literal["pass", "fail", "warning"]


class Evidence(BaseModel):
    source_file: str
    page: int | None = None
    row: int | None = None
    snippet: str
    method: str


class NormalizedValue(BaseModel):
    value: str | int | float | list[float] | None = None
    unit: str | None = None
    display: str | None = None


class ValidationResult(BaseModel):
    rule: str
    status: ValidationStatus
    message: str


class ProductAttribute(BaseModel):
    field: str
    raw_value: str | None = None
    normalized_value: NormalizedValue | None = None
    normalization_explanation: str | None = None
    status: FieldStatus
    confidence: float = Field(ge=0, le=1)
    confidence_label: str = "Deterministic review heuristic — not a probability or accuracy claim."
    evidence: list[Evidence] = Field(default_factory=list)
    validation_results: list[ValidationResult] = Field(default_factory=list)
    review_status: ReviewStatus = "pending"
    review_note: str | None = None
    reviewed_value: str | None = None
    agent_decision: str | None = None
    agent_reason: str | None = None


class ProductRecord(BaseModel):
    id: str
    category: Literal["industrial_valves_fittings"] = "industrial_valves_fittings"
    source_kind: Literal["synthetic_demo", "uploaded", "manual"] = "uploaded"
    attributes: list[ProductAttribute]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReviewRequest(BaseModel):
    action: Literal["approve", "reject", "edit"]
    note: str | None = Field(default=None, max_length=1000)
    value: str | None = Field(default=None, max_length=1000)


class RecordOption(BaseModel):
    """A safely segmented source record available for reviewer selection."""

    index: int = Field(ge=0)
    label: str
    source_file: str
    page: int | None = None
    detected_fields: list[str] = Field(default_factory=list)


class EnrichmentResponse(BaseModel):
    product: ProductRecord
    message: str
    record_options: list[RecordOption] = Field(default_factory=list)
    ai_candidate_count: int = Field(default=0, ge=0)


class BatchResponse(BaseModel):
    products: list[ProductRecord]
    metrics: dict
    message: str


class ReviewAgentToolTrace(BaseModel):
    """A local tool call made by the bounded Evidence Review Agent."""

    tool: Literal[
        "identify_exceptions",
        "inspect_provenance",
        "evaluate_validation",
        "rank_human_actions",
        "evidence_extraction",
        "normalization_check",
        "validation_check",
        "conflict_resolution",
        "decision_agent",
        "policy_engine",
    ]
    outcome: str
    item_count: int = Field(ge=0)


class ReviewAgentTask(BaseModel):
    field: str
    status: FieldStatus
    review_status: ReviewStatus
    priority: int = Field(ge=0)
    recommended_action: Literal["resolve_conflict", "find_source_value", "verify_candidate"]
    reason: str
    evidence_count: int = Field(ge=0)
    human_approval_required: bool = True


class ReviewAgentPlan(BaseModel):
    id: str
    product_id: str
    agent_name: str = "Evidence Review Agent"
    mode: Literal["bounded_local_orchestration"] = "bounded_local_orchestration"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tool_trace: list[ReviewAgentToolTrace]
    tasks: list[ReviewAgentTask]
    summary: str
    mutations_made: bool = False
    human_approval_required: bool = True
    guardrail: str = "The agent only inspects retained evidence and validation output. It cannot change values, resolve conflicts, approve fields, or export data."


class AgentDecision(BaseModel):
    product_id: str
    attribute_field: str
    agent_name: str
    agent_action: str
    input_context: str | None = None
    output: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str | None = None
    confidence: float = 1.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

