from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict
from langgraph.graph import END, StateGraph

from ..core.policies import PolicyEngine
from ..extraction import FIELD_ORDER
from ..models import (
    AgentDecision,
    Evidence,
    NormalizedValue,
    ProductAttribute,
    ProductRecord,
    ReviewAgentPlan,
    ReviewAgentTask,
    ReviewAgentToolTrace,
)
from .conflict_agent import ConflictAgent
from .decision_agent import DecisionAgent
from .evidence_agent import EvidenceAgent
from .normalization_agent import NormalizationAgent
from .validation_agent import ValidationAgent
from ..normalization import normalize_value


REQUIRED_FIELDS = {
    "manufacturer",
    "manufacturer_part_number",
    "product_type",
    "material",
    "size",
    "end_connection",
    "pressure_rating",
}


# Shared strongly-typed CatalogState
class CatalogGraphState(TypedDict):
    product_id: str
    attributes: dict[str, ProductAttribute]
    source_context: str
    historical_corrections: list[dict]
    trace: list[ReviewAgentToolTrace]
    tasks: list[ReviewAgentTask]
    summary: str
    decisions: list[AgentDecision]
    iteration_count: int


# ----------------------------------------------------
# LangGraph Nodes
# ----------------------------------------------------

def evidence_extraction_node(state: CatalogGraphState) -> CatalogGraphState:
    """Evidence Agent Node - extracts raw values and locations."""
    product_id = state["product_id"]
    attributes = state["attributes"]
    context = state["source_context"]
    trace = list(state["trace"])
    decisions = list(state["decisions"])
    iter_count = state["iteration_count"] + 1

    agent = EvidenceAgent()
    extracted_count = 0

    # Determine filename
    filename = "unknown_source.pdf"
    for attr in attributes.values():
        for ev in attr.evidence:
            if ev.source_file and ev.source_file not in {"Manual entry", "Agent Graph Ingestion"}:
                filename = ev.source_file
                break

    for field in FIELD_ORDER:
        attr = attributes.get(field)
        # Extract if missing raw value or on retry loops to find additional evidence for conflict/missing
        should_extract = False
        if not attr or not attr.raw_value:
            should_extract = True
        elif iter_count > 1 and attr.status in {"conflict", "missing"}:
            should_extract = True

        if should_extract:
            res = agent.run(field, context, filename)
            if res:
                extracted_count += 1
                evidence_obj = Evidence(
                    source_file=res["source_file"],
                    page=res["page"],
                    row=res["row"],
                    snippet=res["snippet"],
                    method="agent_extraction_node",
                )
                
                if not attr:
                    attr = ProductAttribute(field=field, status="inferred", confidence=res["confidence"])
                    attributes[field] = attr

                attr.raw_value = res["value"]
                # Append if not duplicate snippet
                if not any(e.snippet == evidence_obj.snippet for e in attr.evidence):
                    attr.evidence.append(evidence_obj)
                attr.status = "inferred"
                attr.confidence = res["confidence"]

                decisions.append(
                    AgentDecision(
                        product_id=product_id,
                        attribute_field=field,
                        agent_name="Evidence Agent",
                        agent_action="extract_attribute",
                        input_context=f"Field: {field}, Iteration: {iter_count}",
                        output=res["value"],
                        evidence_ids=[filename],
                        reason=f"Verbatim quote: “{res['snippet']}”",
                        confidence=res["confidence"],
                    )
                )

    trace.append(
        ReviewAgentToolTrace(
            tool="evidence_extraction",
            input=f"Scan context for fields. Iteration: {iter_count}",
            outcome=f"Evidence Agent scanned document. Extracted {extracted_count} raw attribute(s).",
            item_count=extracted_count,
        )
    )
    return {
        **state,
        "attributes": attributes,
        "trace": trace,
        "decisions": decisions,
        "iteration_count": iter_count,
    }


def normalization_agent_node(state: CatalogGraphState) -> CatalogGraphState:
    """Normalization Agent Node - standardizes materials, connections, and units."""
    product_id = state["product_id"]
    attributes = state["attributes"]
    trace = list(state["trace"])
    decisions = list(state["decisions"])

    agent = NormalizationAgent()
    normalized_count = 0

    for field, attr in attributes.items():
        if attr.raw_value and not attr.normalized_value:
            res = agent.run(field, attr.raw_value, state.get("historical_corrections"))
            if res["value"] is not None:
                normalized_count += 1
                attr.normalized_value = NormalizedValue(
                    value=res["value"],
                    unit=res["unit"],
                    display=res["display"],
                )
                attr.normalization_explanation = res["explanation"]
                attr.confidence = (attr.confidence + res["confidence"]) / 2.0

                decisions.append(
                    AgentDecision(
                        product_id=product_id,
                        attribute_field=field,
                        agent_name="Normalization Agent",
                        agent_action="normalize_value",
                        input_context=attr.raw_value,
                        output=res["display"],
                        evidence_ids=[ev.source_file for ev in attr.evidence],
                        reason=res["explanation"],
                        confidence=res["confidence"],
                    )
                )

    trace.append(
        ReviewAgentToolTrace(
            tool="normalization_check",
            input="Normalize raw attribute strings",
            outcome=f"Normalization Agent completed checks. Canonicalized {normalized_count} attribute(s).",
            item_count=normalized_count,
        )
    )
    return {**state, "attributes": attributes, "trace": trace, "decisions": decisions}


def validation_agent_node(state: CatalogGraphState) -> CatalogGraphState:
    """Validation Agent Node - runs schema rules and safety boundaries."""
    product_id = state["product_id"]
    attributes = state["attributes"]
    trace = list(state["trace"])
    decisions = list(state["decisions"])

    agent = ValidationAgent()
    validation_count = 0

    for field, attr in attributes.items():
        res = agent.run(field, attr.normalized_value, attr.raw_value or "", attributes)
        attr.validation_results = res
        validation_count += len(res)

        fails = [v for v in res if v.status == "fail"]
        if fails:
            decisions.append(
                AgentDecision(
                    product_id=product_id,
                    attribute_field=field,
                    agent_name="Validation Agent",
                    agent_action="validate_constraints",
                    input_context=f"Value: {attr.raw_value}",
                    output="fail",
                    evidence_ids=[ev.source_file for ev in attr.evidence],
                    reason=f"Failing checks: {', '.join(v.rule for v in fails)}",
                    confidence=1.0,
                )
            )

    trace.append(
        ReviewAgentToolTrace(
            tool="validation_check",
            input="Evaluate schema rules and physical boundaries",
            outcome=f"Validation Agent evaluated rules. Registered {validation_count} constraint status checks.",
            item_count=validation_count,
        )
    )
    return {**state, "attributes": attributes, "trace": trace, "decisions": decisions}


def conflict_agent_node(state: CatalogGraphState) -> CatalogGraphState:
    """Cross-Source Conflict Agent Node - compares evidence and detects duplicates."""
    product_id = state["product_id"]
    attributes = state["attributes"]
    context = state["source_context"]
    trace = list(state["trace"])
    decisions = list(state["decisions"])

    agent = ConflictAgent()
    resolved_count = 0

    for field, attr in attributes.items():
        # Reconstruct candidates context from attribute evidence
        candidates = []
        for ev in attr.evidence:
            norm_val, _ = normalize_value(field, ev.snippet)
            candidates.append(
                {
                    "raw_value": ev.snippet,
                    "normalized_display": norm_val.display if norm_val else ev.snippet,
                    "evidence": ev,
                }
            )

        if len(candidates) > 1:
            res = agent.run(field, candidates, context)
            if res["conflict"]:
                resolved_count += 1
                attr.status = "conflict"
                attr.reviewed_value = res["recommended_value"]
                attr.review_note = res["reason"]
                attr.confidence = (attr.confidence + res["confidence"]) / 2.0

                decisions.append(
                    AgentDecision(
                        product_id=product_id,
                        attribute_field=field,
                        agent_name="Conflict Agent",
                        agent_action="detect_conflict",
                        input_context=f"Candidates: {len(candidates)}",
                        output=res["recommended_value"],
                        evidence_ids=[ev.source_file for ev in attr.evidence],
                        reason=res["reason"],
                        confidence=res["confidence"],
                    )
                )

    trace.append(
        ReviewAgentToolTrace(
            tool="conflict_resolution",
            input="Compare PDF vs CSV vs XLSX sources for inconsistencies",
            outcome=f"Conflict Agent flagged or proposed resolution on {resolved_count} attribute conflict(s).",
            item_count=resolved_count,
        )
    )
    return {**state, "attributes": attributes, "trace": trace, "decisions": decisions}


def decision_agent_node(state: CatalogGraphState) -> CatalogGraphState:
    """Decision Agent Node - computes evidence-based confidence and suggests routing."""
    product_id = state["product_id"]
    attributes = state["attributes"]
    trace = list(state["trace"])
    decisions = list(state["decisions"])

    agent = DecisionAgent()
    decision_count = 0

    for field, attr in attributes.items():
        attr_data = {
            "raw_value": attr.raw_value,
            "normalized_display": attr.normalized_value.display if attr.normalized_value else None,
            "status": attr.status,
            "evidence": [{"method": ev.method, "evidence_type": ev.method} for ev in attr.evidence],
            "validation_results": [{"rule": v.rule, "status": v.status} for v in attr.validation_results],
        }

        res = agent.run(field, attr_data)
        decision_count += 1

        attr.agent_decision = res["decision"]
        attr.agent_reason = res["reason"]
        attr.confidence = res["confidence"]

        decisions.append(
            AgentDecision(
                product_id=product_id,
                attribute_field=field,
                agent_name="Decision Agent",
                agent_action="evaluate_confidence",
                input_context=f"Status: {attr.status}",
                output=res["decision"],
                evidence_ids=[ev.source_file for ev in attr.evidence],
                reason=res["reason"],
                confidence=res["confidence"],
            )
        )

    trace.append(
        ReviewAgentToolTrace(
            tool="decision_agent",
            input="Review all agent outputs and calculate confidence matrix",
            outcome=f"Decision Agent processed {decision_count} attribute routing decision(s).",
            item_count=decision_count,
        )
    )
    return {**state, "attributes": attributes, "trace": trace, "decisions": decisions}


def policy_engine_node(state: CatalogGraphState) -> CatalogGraphState:
    """Policy Engine Node - enforces deterministic rules before DB write."""
    product_id = state["product_id"]
    attributes = state["attributes"]
    trace = list(state["trace"])
    decisions = list(state["decisions"])

    verified_count = 0
    escalated_count = 0

    for field, attr in attributes.items():
        decision, reason = PolicyEngine.evaluate(attr)
        
        if decision == "AUTO_VERIFY" and attr.agent_decision == "AUTO_VERIFY":
            verified_count += 1
            # Apply approved values to catalog
            attr.review_status = "approved"
            attr.reviewed_value = attr.normalized_value.display if attr.normalized_value else attr.raw_value
            attr.review_note = f"Auto-verified by Policy Engine. {reason}"
        else:
            escalated_count += 1
            attr.review_status = "pending"
            attr.review_note = f"Human Review Escalation: {reason}"
            if attr.agent_decision == "AUTO_VERIFY":
                attr.agent_decision = "HUMAN_REVIEW"
            attr.agent_reason = reason

        decisions.append(
            AgentDecision(
                product_id=product_id,
                attribute_field=field,
                agent_name="Policy Engine",
                agent_action="verify_or_escalate",
                input_context=decision,
                output=attr.review_status,
                evidence_ids=[ev.source_file for ev in attr.evidence],
                reason=reason,
                confidence=attr.confidence,
            )
        )

    trace.append(
        ReviewAgentToolTrace(
            tool="policy_engine",
            input="Enforce verification policies",
            outcome=f"Policy Engine verified {verified_count} and escalated {escalated_count} field(s).",
            item_count=verified_count,
        )
    )
    return {**state, "attributes": attributes, "trace": trace, "decisions": decisions}


# ----------------------------------------------------
# 3. Graph Routing
# ----------------------------------------------------

def route_after_conflict(state: CatalogGraphState) -> str:
    """Routes state based on conflict analysis and iteration count."""
    attributes = state["attributes"]
    iter_count = state["iteration_count"]

    # Search if there is any unresolved conflict and we haven't looped yet
    has_conflict = any(attr.status == "conflict" for attr in attributes.values())
    if has_conflict and iter_count == 1:
        return "evidence_extraction"
    return "decision_agent"


# ----------------------------------------------------
# 4. Graph Construction and Compiler
# ----------------------------------------------------

def build_catalog_state_graph() -> StateGraph:
    builder = StateGraph(CatalogGraphState)
    
    # Register Node functions
    builder.add_node("evidence_extraction", evidence_extraction_node)
    builder.add_node("normalization_check", normalization_agent_node)
    builder.add_node("validation_check", validation_agent_node)
    builder.add_node("conflict_resolution", conflict_agent_node)
    builder.add_node("decision_agent", decision_agent_node)
    builder.add_node("policy_engine", policy_engine_node)
    
    # Setup Edge connections
    builder.set_entry_point("evidence_extraction")
    builder.add_edge("evidence_extraction", "normalization_check")
    builder.add_edge("normalization_check", "validation_check")
    builder.add_edge("validation_check", "conflict_resolution")
    
    # Conditional routing after Conflict Resolution
    builder.add_conditional_edges(
        "conflict_resolution",
        route_after_conflict,
        {
            "evidence_extraction": "evidence_extraction",
            "decision_agent": "decision_agent",
        },
    )
    
    builder.add_edge("decision_agent", "policy_engine")
    builder.add_edge("policy_engine", END)
    
    return builder.compile()


def run_orchestrator_graph(product: ProductRecord, source_context: str, historical_corrections: list[dict] = None) -> tuple[ReviewAgentPlan, list[ProductAttribute], list[AgentDecision]]:
    # Convert list attributes to dict for state mapping
    attr_dict = {attr.field: attr.model_copy(deep=True) for attr in product.attributes}
    
    # Initialize state
    initial_state: CatalogGraphState = {
        "product_id": product.id,
        "attributes": attr_dict,
        "source_context": source_context,
        "historical_corrections": historical_corrections or [],
        "trace": [],
        "tasks": [],
        "summary": "",
        "decisions": [],
        "iteration_count": 0,
    }
    
    # Execute state graph
    graph = build_catalog_state_graph()
    final_state = graph.invoke(initial_state)
    
    # Compile tasks lists
    exceptions: list[ProductAttribute] = []
    for field, attr in final_state["attributes"].items():
        if attr.agent_decision in {"HUMAN_REVIEW", "CONFLICT", "MISSING"}:
            exceptions.append(attr)
            
    tasks: list[ReviewAgentTask] = []
    for attr in exceptions:
        priority = 0
        if attr.status == "conflict" or attr.agent_decision == "CONFLICT":
            priority += 100
            action = "resolve_conflict"
            reason_text = attr.agent_reason or "Competing source documentation provides conflicting values."
        elif attr.status == "missing" or attr.agent_decision == "MISSING":
            priority += 80 if attr.field in REQUIRED_FIELDS else 35
            action = "find_source_value"
            if attr.field in REQUIRED_FIELDS:
                reason_text = "Locate an authorised source (technical datasheet, web page, or catalog PDF) containing the required product specifications."
            else:
                reason_text = "Check source documentation to see if this optional attribute is available."
        else:
            priority += 55
            action = "verify_candidate"
            reason_text = attr.agent_reason or "Validate the recommended attribute value against source evidence."
            
        tasks.append(
            ReviewAgentTask(
                field=attr.field,
                status=attr.status,
                review_status=attr.review_status,
                priority=priority,
                recommended_action=action,
                reason=reason_text,
                evidence_count=len(attr.evidence),
                human_approval_required=True,
            )
        )
        
    tasks = sorted(tasks, key=lambda t: (-t.priority, t.field))
    
    summary = (
        "Agent completed real-time Graph checks. No exception fields were found."
        if not tasks
        else f"Agent completed real-time Graph checks. Found {len(tasks)} exception(s) ranked by priority."
    )
    
    plan = ReviewAgentPlan(
        id=f"ra_graph_{uuid.uuid4().hex[:12]}",
        product_id=product.id,
        tool_trace=final_state["trace"],
        tasks=tasks,
        summary=summary,
        mutations_made=any(attr.review_status == "approved" for attr in final_state["attributes"].values()),
    )
    
    return plan, list(final_state["attributes"].values()), final_state["decisions"]

