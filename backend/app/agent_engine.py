from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .config import AI_API_KEY, AI_BASE_URL, AI_MODEL, ai_is_configured
from .extraction import FIELD_ORDER
from .models import Evidence, NormalizedValue, ProductAttribute, ProductRecord, ReviewAgentPlan, ReviewAgentTask, ReviewAgentToolTrace, ValidationResult
from .normalization import normalize_value, normalized_key
REQUIRED_FIELDS = {
    "manufacturer",
    "manufacturer_part_number",
    "product_type",
    "material",
    "size",
    "end_connection",
    "pressure_rating",
}

# ----------------------------------------------------
# 1. Pydantic schemas for LangChain Structured Outputs
# ----------------------------------------------------
class AIExtractedAttribute(BaseModel):
    field: str = Field(description="The allowed attribute field name (must be from FIELD_ORDER)")
    raw_value: str = Field(description="The exact raw string value extracted from the source text")
    source_quote: str = Field(description="The short verbatim quote from the text that supports this value")


class AIExtractedPayload(BaseModel):
    attributes: list[AIExtractedAttribute] = Field(default_factory=list)


class ConflictResolutionPayload(BaseModel):
    resolved_value: str = Field(description="The value selected to resolve the conflict")
    reason: str = Field(description="Explanation for why this value is selected based on the context evidence")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0 representing selection certainty")


# ----------------------------------------------------
# 2. LangGraph State Definition
# ----------------------------------------------------
class CatalogGraphState(TypedDict):
    product_id: str
    attributes: dict[str, ProductAttribute]
    source_context: str
    trace: list[ReviewAgentToolTrace]
    tasks: list[ReviewAgentTask]
    summary: str


# ----------------------------------------------------
# 3. LangGraph Node Functions
# ----------------------------------------------------

def evidence_extraction_node(state: CatalogGraphState) -> CatalogGraphState:
    """Evidence Extraction Agent Node.

    Runs real-time LLM structured extraction over the context for missing fields.
    """
    trace = list(state.get("trace") or [])
    attributes = dict(state["attributes"])
    source_context = state["source_context"]
    
    missing_fields = [
        field for field in FIELD_ORDER 
        if attributes[field].status == "missing"
    ]
    
    outcome = "No missing fields to extract."
    extracted_count = 0
    
    if missing_fields and source_context:
        if ai_is_configured():
            try:
                llm = ChatOpenAI(
                    openai_api_key=AI_API_KEY,
                    openai_api_base=AI_BASE_URL,
                    model_name=AI_MODEL,
                    temperature=0,
                )
                structured_llm = llm.with_structured_output(AIExtractedPayload)
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", (
                        "You are a cautious industrial-catalog candidate extraction assistant.\n"
                        "Return JSON only containing attributes from this list: {allowed_fields}.\n"
                        "Only return values that occur verbatim in the supplied text."
                    )),
                    ("user", "Source text:\n---\n{context}\n---")
                ])
                
                chain = prompt | structured_llm
                response: AIExtractedPayload = chain.invoke({
                    "allowed_fields": ", ".join(missing_fields),
                    "context": source_context[:12000]
                })
                
                for item in response.attributes:
                    if item.field in missing_fields and item.raw_value.strip():
                        # Grounded verification
                        if item.raw_value.lower() in source_context.lower() and item.source_quote.lower() in source_context.lower():
                            attr = attributes[item.field]
                            attr.raw_value = item.raw_value.strip()
                            attr.status = "inferred"
                            attr.evidence.append(
                                Evidence(
                                    source_file="Agent Graph Ingestion",
                                    snippet=item.source_quote.strip()[:500],
                                    method="agent_extraction_node"
                                )
                            )
                            extracted_count += 1
                
                outcome = f"AI Agent ran real-time extraction for fields {missing_fields} and found {extracted_count} candidates."
            except Exception as e:
                outcome = f"AI extraction node encountered an error: {str(e)}. Retained local deterministic state."
        else:
            outcome = "Optional AI is not configured. Running in deterministic mode."

    trace.append(
        ReviewAgentToolTrace(
            tool="evidence_extraction",
            outcome=outcome,
            item_count=extracted_count
        )
    )
    return {**state, "attributes": attributes, "trace": trace}


def normalization_check_node(state: CatalogGraphState) -> CatalogGraphState:
    """Normalization Agent Node.

    Runs unit conversions and standardizes materials in the graph state.
    """
    trace = list(state.get("trace") or [])
    attributes = dict(state["attributes"])
    normalized_count = 0
    
    for field, attr in attributes.items():
        if attr.raw_value and attr.status != "missing" and not attr.normalized_value:
            normalized, explanation = normalize_value(field, attr.raw_value)
            if normalized:
                attr.normalized_value = normalized
                attr.normalization_explanation = explanation
                normalized_count += 1
                
    trace.append(
        ReviewAgentToolTrace(
            tool="normalization_check",
            outcome=f"Standardized and normalized {normalized_count} attribute values.",
            item_count=normalized_count
        )
    )
    return {**state, "attributes": attributes, "trace": trace}


def validation_check_node(state: CatalogGraphState) -> CatalogGraphState:
    """Validation Agent Node.

    Applies required schema rules, unit parsing, and plausibility boundary warnings.
    """
    trace = list(state.get("trace") or [])
    attributes = dict(state["attributes"])
    validation_failures = 0
    
    for field, attr in attributes.items():
        validations: list[ValidationResult] = []
        
        # 1. Missing Required check
        if attr.status == "missing":
            if field in REQUIRED_FIELDS:
                validations.append(
                    ValidationResult(
                        rule="required_field",
                        status="fail",
                        message="Required PIM attribute has no source evidence."
                    )
                )
                validation_failures += 1
            else:
                validations.append(
                    ValidationResult(
                        rule="optional_field",
                        status="warning",
                        message="Optional field has no source evidence."
                    )
                )
        else:
            # 2. Check value and unit parse
            if field in {"size", "pressure_rating", "temperature_range"}:
                if not attr.normalized_value:
                    validations.append(
                        ValidationResult(
                            rule="value_and_unit_parse",
                            status="fail",
                            message="Numeric value or compatible unit could not be parsed."
                        )
                    )
                    validation_failures += 1
                else:
                    validations.append(
                        ValidationResult(
                            rule="value_and_unit_parse",
                            status="pass",
                            message="Successfully parsed value and compatible unit."
                        )
                    )
            
            # 3. Domain Plausibility checks
            if field == "size" and attr.normalized_value:
                val = attr.normalized_value.value
                if isinstance(val, (int, float)) and val <= 0:
                    validations.append(
                        ValidationResult(
                            rule="positive_size",
                            status="fail",
                            message="PIM size must be a positive value."
                        )
                    )
                    validation_failures += 1
            
            if field == "pressure_rating" and attr.normalized_value:
                val = attr.normalized_value.value
                if isinstance(val, (int, float)):
                    # Cross-field checks (Brass ball valve pressure limit)
                    material = attributes.get("material")
                    p_type = attributes.get("product_type")
                    mat_str = (material.raw_value or "").lower() if material else ""
                    type_str = (p_type.raw_value or "").lower() if p_type else ""
                    
                    if "brass" in mat_str and "ball" in type_str and attr.normalized_value.unit == "WOG" and val > 1000:
                        validations.append(
                            ValidationResult(
                                rule="brass_ball_valve_pressure_plausibility",
                                status="fail",
                                message="Brass ball valve WOG pressure rating exceeding 1,000 WOG requires reviewer clearance."
                            )
                        )
                        validation_failures += 1
                        attr.status = "conflict"
                        
        attr.validation_results = validations
        
    trace.append(
        ReviewAgentToolTrace(
            tool="validation_check",
            outcome=f"Executed schema checks. Detected {validation_failures} rule exception(s).",
            item_count=validation_failures
        )
    )
    return {**state, "attributes": attributes, "trace": trace}


def conflict_resolution_node(state: CatalogGraphState) -> CatalogGraphState:
    """Conflict Resolution Agent Node.

    Uses LLM reasoning to evaluate conflicting attributes and write proposals.
    """
    trace = list(state.get("trace") or [])
    attributes = dict(state["attributes"])
    source_context = state["source_context"]
    resolved_count = 0
    outcome = "No conflicts detected."
    
    conflict_fields = [
        field for field, attr in attributes.items() 
        if attr.status == "conflict"
    ]
    
    if conflict_fields:
        if ai_is_configured() and source_context:
            try:
                llm = ChatOpenAI(
                    openai_api_key=AI_API_KEY,
                    openai_api_base=AI_BASE_URL,
                    model_name=AI_MODEL,
                    temperature=0,
                )
                structured_llm = llm.with_structured_output(ConflictResolutionPayload)
                
                for field in conflict_fields:
                    attr = attributes[field]
                    
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", (
                            "You are an expert industrial Valve and Fitting catalog data auditor.\n"
                            "Your job is to resolve a conflict on the product attribute '{field}'.\n"
                            "Analyze the provided source context carefully. Look for annotations, notes, or closest keywords.\n"
                            "Select the correct resolved value and explain your reasoning clearly."
                        )),
                        ("user", (
                            "Conflicting Value in State: {current_value}\n"
                            "Evidence Snippets: {snippets}\n"
                            "Full Catalog Context:\n---\n{context}\n---"
                        ))
                    ])
                    
                    snippets_str = "; ".join(f"“{ev.snippet}”" for ev in attr.evidence)
                    
                    chain = prompt | structured_llm
                    response: ConflictResolutionPayload = chain.invoke({
                        "field": field,
                        "current_value": attr.raw_value or "None",
                        "snippets": snippets_str,
                        "context": source_context[:10000]
                    })
                    
                    # Update with suggested choice
                    attr.review_note = f"Agent resolution: {response.reason} (Confidence: {response.confidence:.2f})"
                    attr.reviewed_value = response.resolved_value
                    attr.review_status = "edited"
                    resolved_count += 1
                
                outcome = f"Conflict Agent analyzed {len(conflict_fields)} conflicts and proposed resolution values."
            except Exception as e:
                outcome = f"Conflict Agent node failed: {str(e)}. Flagged conflicts for manual reviewer."
        else:
            outcome = f"Conflict Agent active. Flagged {len(conflict_fields)} attribute conflicts for manual human review."

    trace.append(
        ReviewAgentToolTrace(
            tool="conflict_resolution",
            outcome=outcome,
            item_count=resolved_count
        )
    )
    return {**state, "attributes": attributes, "trace": trace}


# ----------------------------------------------------
# 4. Graph Construction and Compiler
# ----------------------------------------------------
from langgraph.graph import StateGraph, END

def build_review_graph() -> StateGraph:
    builder = StateGraph(CatalogGraphState)
    
    # Register Node functions
    builder.add_node("evidence_extraction", evidence_extraction_node)
    builder.add_node("normalization_check", normalization_check_node)
    builder.add_node("validation_check", validation_check_node)
    builder.add_node("conflict_resolution", conflict_resolution_node)
    
    # Setup Edge connections
    builder.set_entry_point("evidence_extraction")
    builder.add_edge("evidence_extraction", "normalization_check")
    builder.add_edge("normalization_check", "validation_check")
    builder.add_edge("validation_check", "conflict_resolution")
    builder.add_edge("conflict_resolution", END)
    
    return builder.compile()


# ----------------------------------------------------
# 5. Core Execution Runner
# ----------------------------------------------------
def run_agent_graph(product: ProductRecord, source_context: str) -> tuple[ReviewAgentPlan, list[ProductAttribute]]:
    # Convert list attributes to dict for state mapping
    attr_dict = {attr.field: attr.model_copy(deep=True) for attr in product.attributes}
    
    # Initialize state
    initial_state: CatalogGraphState = {
        "product_id": product.id,
        "attributes": attr_dict,
        "source_context": source_context,
        "trace": [],
        "tasks": [],
        "summary": "",
    }
    
    # Execute state graph
    graph = build_review_graph()
    final_state = graph.invoke(initial_state)
    
    # Run the ranking step (replaces rank_human_actions step)
    exceptions: list[ProductAttribute] = []
    validation_failures: set[str] = set()
    
    for field, attr in final_state["attributes"].items():
        if attr.status in {"conflict", "missing", "inferred"} or any(v.status == "fail" for v in attr.validation_results):
            exceptions.append(attr)
        if any(v.status == "fail" for v in attr.validation_results):
            validation_failures.add(field)
            
    tasks: list[ReviewAgentTask] = []
    for attr in exceptions:
        priority = 0
        if attr.status == "conflict":
            priority += 100
            action = "resolve_conflict"
            reason = "Competing normalized values are retained. Compare every source reference before choosing a reviewed value."
        elif attr.status == "missing":
            priority += 80 if attr.field in REQUIRED_FIELDS else 35
            action = "find_source_value"
            reason = (
                "This required PIM field has no retained source value. Locate an authorised source or keep the gap explicit."
                if attr.field in REQUIRED_FIELDS
                else "No direct source value is retained for this optional field. Do not invent a replacement."
            )
        else:
            priority += 55
            action = "verify_candidate"
            reason = "This is an inferred candidate. Confirm its retained source quote before approving it."
            
        if attr.field in validation_failures:
            priority += 20
            reason += " A deterministic validation rule also failed; inspect its rule message before making the human decision."
        if attr.review_status == "pending":
            priority += 5

            
        tasks.append(
            ReviewAgentTask(
                field=attr.field,
                status=attr.status,
                review_status=attr.review_status,
                priority=priority,
                recommended_action=action,
                reason=reason,
                evidence_count=len(attr.evidence),
            )
        )
        
    tasks = sorted(tasks, key=lambda t: (-t.priority, t.field))
    
    summary = (
        "Agent completed real-time Graph checks. No exception fields were found."
        if not tasks
        else f"Agent completed real-time Graph checks. Found {len(tasks)} exception(s) ranked by priority."
    )
    
    # Build complete response plan
    plan = ReviewAgentPlan(
        id=f"ra_graph_{uuid.uuid4().hex[:12]}",
        product_id=product.id,
        tool_trace=final_state["trace"],
        tasks=tasks,
        summary=summary,
        mutations_made=any(attr.review_status == "edited" for attr in final_state["attributes"].values()),
    )
    return plan, list(final_state["attributes"].values())

