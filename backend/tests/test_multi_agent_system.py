from __future__ import annotations

import pytest
from pathlib import Path
from app.models import ProductAttribute, Evidence, ValidationResult, NormalizedValue, ProductRecord
from app.core.policies import PolicyEngine, get_source_weight
from app.agents.evidence_agent import EvidenceAgent
from app.agents.normalization_agent import NormalizationAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.conflict_agent import ConflictAgent
from app.agents.decision_agent import DecisionAgent
from app.agents.orchestrator import run_orchestrator_graph


def test_evidence_agent_fallback() -> None:
    agent = EvidenceAgent()
    # Test deterministic fallback extraction
    res = agent.run("size", "We ordered a 25.4 mm ball valve for construction.", "catalog.pdf")
    assert res is not None
    assert res["value"] == "25.4 mm"
    assert "25.4 mm" in res["snippet"]
    assert res["source_file"] == "catalog.pdf"
    assert res["evidence_type"] == "direct"
    assert res["confidence"] == 0.90


def test_normalization_agent() -> None:
    agent = NormalizationAgent()
    # 1. Alias standard test
    res = agent.run("material", "SS304")
    assert res["display"] == "Stainless Steel 304" # matches backend normalization mapping display
    assert res["confidence"] == 0.95

    # 2. Metric conversion size standard test
    res = agent.run("size", "25.4 mm")
    assert res["display"] == "1 in"

    # 3. Unrecognized unknown value test
    res = agent.run("material", "HyperMetalX")
    assert res["display"] == "HyperMetalX"
    assert res["confidence"] == 0.50


def test_validation_agent() -> None:
    agent = ValidationAgent()
    
    # 1. Valid size check (pass confidence=0.90 to satisfy pydantic validation constraints)
    attrs = {"size": ProductAttribute(field="size", raw_value="25.4 mm", status="inferred", confidence=0.90)}
    res = agent.run("size", NormalizedValue(value=1.0, unit="in", display="1 in"), "25.4 mm", attrs)
    assert not any(v.status == "fail" for v in res)

    # 2. Invalid negative size check
    attrs = {"size": ProductAttribute(field="size", raw_value="-5 mm", status="inferred", confidence=0.90)}
    res = agent.run("size", NormalizedValue(value=-5.0, unit="mm", display="-5 mm"), "-5 mm", attrs)
    assert any(v.status == "fail" for v in res)


def test_conflict_agent_ranking() -> None:
    agent = ConflictAgent()
    context = "Datasheet says 600 WOG. CSV lists 400 WOG."
    
    # PDF extraction has weight 5, CSV has weight 2
    candidates = [
        {
            "raw_value": "600 WOG",
            "normalized_display": "600 WOG",
            "evidence": Evidence(source_file="spec.pdf", snippet="600 WOG", method="pdf_table_row_extraction"),
        },
        {
            "raw_value": "400 WOG",
            "normalized_display": "400 WOG",
            "evidence": Evidence(source_file="supplier.csv", snippet="400 WOG", method="csv_row_extraction"),
        }
    ]
    
    res = agent.run("pressure_rating", candidates, context)
    assert res["conflict"] is True
    # Should resolve to the higher-priority PDF source (600 WOG)
    assert res["recommended_value"] == "600 WOG"
    assert "pdf_table_row_extraction" in res["reason"]


def test_decision_agent_confidence() -> None:
    agent = DecisionAgent()
    
    # 1. High confidence case -> AUTO_VERIFY
    attr_data_ok = {
        "raw_value": "600 WOG",
        "normalized_display": "600 WOG",
        "status": "verified",
        "evidence": [{"method": "pdf_table_row_extraction", "evidence_type": "direct"}],
        "validation_results": [{"rule": "pressure_positive", "status": "pass"}],
    }
    res = agent.run("pressure_rating", attr_data_ok)
    assert res["decision"] == "AUTO_VERIFY"
    assert res["confidence"] >= 0.90

    # 2. Failed validation case -> HUMAN_REVIEW
    attr_data_fail = {
        "raw_value": "-10 WOG",
        "normalized_display": "-10 WOG",
        "status": "inferred",
        "evidence": [{"method": "pdf_table_row_extraction", "evidence_type": "direct"}],
        "validation_results": [{"rule": "pressure_positive", "status": "fail"}],
    }
    res = agent.run("pressure_rating", attr_data_fail)
    assert res["decision"] == "HUMAN_REVIEW"


def test_policy_engine_enforcement() -> None:
    # Test that Policy Engine blocks auto-verification if confidence is below threshold
    low_confidence_attr = ProductAttribute(
        field="material",
        raw_value="HyperMetal",
        status="inferred",
        confidence=0.50, # low confidence
        evidence=[Evidence(source_file="spec.pdf", snippet="HyperMetal", method="pdf_text_extraction")],
        validation_results=[],
    )
    decision, reason = PolicyEngine.evaluate(low_confidence_attr)
    assert decision == "HUMAN_REVIEW"
    assert "low confidence" in reason.lower()

    # High confidence attribute passing all checks
    ok_attr = ProductAttribute(
        field="material",
        raw_value="SS304",
        normalized_value=NormalizedValue(value="SS304", display="SS304"),
        status="verified",
        confidence=0.95,
        evidence=[Evidence(source_file="spec.pdf", snippet="SS304", method="pdf_table_row_extraction")],
        validation_results=[ValidationResult(rule="rule", status="pass", message="ok")],
    )
    decision, reason = PolicyEngine.evaluate(ok_attr)
    assert decision == "AUTO_VERIFY"


def test_orchestrator_langgraph_paths() -> None:
    # Verify the full orchestrator path run compiles and behaves cleanly
    product = ProductRecord(
        id="test_sku_1",
        attributes=[
            ProductAttribute(
                field="size",
                raw_value="25.4 mm",
                status="inferred",
                confidence=0.90,
                evidence=[Evidence(source_file="spec.pdf", snippet="25.4 mm", method="pdf_text_extraction")],
            )
        ]
    )
    context = "Catalog contains 25.4 mm specifications."
    plan, attrs, decisions = run_orchestrator_graph(product, context)
    
    assert plan is not None
    assert len(attrs) > 0
    # Should have run all agent nodes (evidence_extraction, normalization_check, validation_check, etc.)
    tools_run = [trace.tool for trace in plan.tool_trace]
    assert "evidence_extraction" in tools_run
    assert "normalization_check" in tools_run
    assert "validation_check" in tools_run
    assert "decision_agent" in tools_run
    assert "policy_engine" in tools_run
    
    # Decisions should be tracked in the audit trail
    assert len(decisions) > 0
    assert any(d.agent_name == "Policy Engine" for d in decisions)


def test_feedback_learning_loop() -> None:
    # Test that human edits are used by the NormalizationAgent as learned corrections
    agent = NormalizationAgent()
    
    historical_corrections = [
        {
            "field": "material",
            "raw_value": "SS-304",
            "reviewed_value": "Stainless Steel 304"
        }
    ]
    
    # 1. Without corrections (falls back to default/unrecognized retention or local Pint normalization)
    # "SS-304" is not directly in standard aliases
    res_no_corr = agent.run("material", "SS-304")
    assert res_no_corr["display"] != "Stainless Steel 304" or res_no_corr["confidence"] < 0.98

    # 2. With corrections (automatically maps to human-approved value with high confidence)
    res_with_corr = agent.run("material", "SS-304", historical_corrections)
    assert res_with_corr["display"] == "Stainless Steel 304"
    assert res_with_corr["confidence"] == 0.98
    assert "Learned from past" in res_with_corr["explanation"]

