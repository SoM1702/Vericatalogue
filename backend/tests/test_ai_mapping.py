from pathlib import Path

from app.ai_mapping import attach_grounded_candidates
from app.extraction import Candidate, SourceRow
from app.models import Evidence
from app.repository import ProductRepository
from app.service import CatalogService


def test_ai_candidate_requires_an_exact_source_quote() -> None:
    source = SourceRow(
        "supplier_notes.pdf",
        "uploaded",
        context="Description: Compact valve for low-temperature media.",
    )
    attached = attach_grounded_candidates(
        source,
        {
            "attributes": [
                {
                    "field": "description",
                    "raw_value": "Compact valve for low-temperature media.",
                    "source_quote": "Description: Compact valve for low-temperature media.",
                },
                {
                    "field": "material",
                    "raw_value": "Stainless Steel 304",
                    "source_quote": "Description: Compact valve for low-temperature media.",
                },
            ]
        },
    )
    assert attached == 1
    candidate = source.candidates["description"][0]
    assert candidate.inferred is True
    assert candidate.evidence.method == "optional_ai_candidate_mapping"


def test_ai_only_candidate_stays_inferred_in_product_record(tmp_path: Path) -> None:
    source = SourceRow(
        "supplier_notes.pdf",
        "uploaded",
        {
            "manufacturer": [Candidate("Northstar", Evidence(source_file="supplier_notes.pdf", page=1, snippet="Manufacturer: Northstar", method="test"))],
        },
        context="Description: Compact valve for low-temperature media.",
    )
    attach_grounded_candidates(
        source,
        {"attributes": [{"field": "description", "raw_value": "Compact valve for low-temperature media.", "source_quote": "Description: Compact valve for low-temperature media."}]},
    )
    product = CatalogService(ProductRepository(tmp_path / "ai.sqlite3")).build_product([source])
    description = next(attribute for attribute in product.attributes if attribute.field == "description")
    assert description.status == "inferred"
    assert description.confidence == 0.55
