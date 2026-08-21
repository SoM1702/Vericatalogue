from pathlib import Path

from app.extraction import Candidate, SourceRow
from app.models import Evidence
from app.repository import ProductRepository
from app.service import CatalogService


def candidate(value: str, source_file: str = "synthetic_source.pdf") -> Candidate:
    return Candidate(value, Evidence(source_file=source_file, page=1, snippet=value, method="test"))


def complete_source(pressure: str = "600 WOG") -> SourceRow:
    return SourceRow(
        "synthetic_source.pdf",
        "synthetic_demo",
        {
            "manufacturer": [candidate("Northstar Flow Systems")],
            "manufacturer_part_number": [candidate("NFS-AGENT-1001")],
            "product_title": [candidate("1 in Full Port Ball Valve")],
            "product_type": [candidate("Ball Valve")],
            "material": [candidate("SS304")],
            "size": [candidate("25.4 mm")],
            "end_connection": [candidate("NPT")],
            "pressure_rating": [candidate(pressure)],
        },
    )


def test_review_agent_prioritizes_conflict_and_keeps_product_unchanged(tmp_path: Path) -> None:
    service = CatalogService(ProductRepository(tmp_path / "agent.sqlite3"))
    product = service.enrich([complete_source("600 WOG"), complete_source("400 WOG")])

    plan = service.run_review_agent(product.id)

    assert plan is not None
    assert plan.mutations_made is False
    assert plan.human_approval_required is True
    # The multi-agent orchestrator loops once when conflict is detected, then runs decision and policy engine
    assert [trace.tool for trace in plan.tool_trace] == [
        "evidence_extraction",
        "normalization_check",
        "validation_check",
        "conflict_resolution",
        "evidence_extraction",
        "normalization_check",
        "validation_check",
        "conflict_resolution",
        "decision_agent",
        "policy_engine",
    ]
    assert plan.tasks[0].field == "pressure_rating"
    assert plan.tasks[0].recommended_action == "resolve_conflict"
    assert plan.tasks[0].evidence_count == 2
    unchanged = service.repository.get(product.id)
    assert unchanged is not None
    pressure = next(attribute for attribute in unchanged.attributes if attribute.field == "pressure_rating")
    assert pressure.status == "conflict"
    assert pressure.review_status == "pending"
    persisted = service.repository.latest_review_agent_run(product.id)
    assert persisted is not None
    assert persisted.id == plan.id


def test_review_agent_requires_source_or_human_review_for_missing_required_field(tmp_path: Path) -> None:
    service = CatalogService(ProductRepository(tmp_path / "missing.sqlite3"))
    source = complete_source()
    source.candidates.pop("material")
    product = service.enrich([source])

    plan = service.run_review_agent(product.id)

    assert plan is not None
    task = next(item for item in plan.tasks if item.field == "material")
    assert task.status == "missing"
    assert task.recommended_action == "find_source_value"
    assert task.human_approval_required is True
    assert "Locate an authorised source" in task.reason
