from pathlib import Path

from app.extraction import Candidate, SourceRow
from app.models import Evidence, ReviewRequest
from app.repository import ProductRepository
from app.service import CatalogService


def candidate(value: str, file_name: str = "synthetic_source.pdf") -> Candidate:
    return Candidate(value, Evidence(source_file=file_name, page=1, snippet=value, method="test"))


def complete_source(pressure: str = "600 WOG") -> SourceRow:
    return SourceRow(
        "synthetic_source.pdf",
        "synthetic_demo",
        {
            "manufacturer": [candidate("Northstar Flow Systems")],
            "manufacturer_part_number": [candidate("NFS-BV-1001")],
            "product_title": [candidate("1 in Full Port Ball Valve")],
            "product_type": [candidate("Ball Valve")],
            "material": [candidate("SS304")],
            "size": [candidate("25.4 mm")],
            "end_connection": [candidate("NPT")],
            "pressure_rating": [candidate(pressure)],
            "temperature_range": [candidate("-20 C to 180 C")],
        },
    )


def make_service(tmp_path: Path) -> CatalogService:
    return CatalogService(ProductRepository(tmp_path / "test.sqlite3"))


def test_evidence_is_retained_and_exported(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    product = service.enrich([complete_source()])
    size = next(attribute for attribute in product.attributes if attribute.field == "size")
    assert size.status == "verified"
    assert size.evidence[0].source_file == "synthetic_source.pdf"
    assert "manufacturer_part_number" in service.product_csv(product)


def test_conflicting_pressure_requires_review(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    product = service.enrich([complete_source("600 WOG"), complete_source("400 WOG")])
    pressure = next(attribute for attribute in product.attributes if attribute.field == "pressure_rating")
    assert pressure.status == "conflict"
    assert len(pressure.evidence) == 2
    reviewed = service.review(product.id, "pressure_rating", ReviewRequest(action="approve", note="Validated against source."))
    assert reviewed is not None
    assert next(attribute for attribute in reviewed.attributes if attribute.field == "pressure_rating").review_status == "approved"


def test_missing_required_field_is_not_invented(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    source = complete_source()
    source.candidates.pop("material")
    product = service.enrich([source])
    material = next(attribute for attribute in product.attributes if attribute.field == "material")
    assert material.status == "missing"
    assert material.normalized_value is None


def test_batch_metrics_find_duplicate_candidates(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    products = service.batch([complete_source(), complete_source()])
    metrics = service.health_metrics(products)
    assert metrics["product_count"] == 2
    assert metrics["duplicate_candidate_count"] == 1
