from __future__ import annotations

import csv
from pathlib import Path

from evaluation.run_evaluation import evaluate


def test_evaluation_harness_reports_field_level_measures_without_copying_source(tmp_path: Path) -> None:
    source = tmp_path / "authorised_input.csv"
    source.write_text(
        "manufacturer,manufacturer_part_number,product_type,material,size,end_connection,pressure_rating\n"
        "Atlas Valve Inc.,AT-100,Ball Valve,SS304,25.4 mm,NPT,600 WOG\n",
        encoding="utf-8",
    )
    truth = tmp_path / "ground_truth.csv"
    with truth.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=["case_id", "source_path", "record_index", "field", "expected_value", "expected_status"])
        writer.writeheader()
        writer.writerows(
            [
                {"case_id": "atlas-100", "source_path": source.name, "record_index": 0, "field": "manufacturer", "expected_value": "Atlas Valve Inc.", "expected_status": "verified"},
                {"case_id": "atlas-100", "source_path": source.name, "record_index": 0, "field": "manufacturer_part_number", "expected_value": "AT-100", "expected_status": "verified"},
                {"case_id": "atlas-100", "source_path": source.name, "record_index": 0, "field": "size", "expected_value": "1 in", "expected_status": "verified"},
                {"case_id": "atlas-100", "source_path": source.name, "record_index": 0, "field": "certifications", "expected_value": "", "expected_status": "missing"},
            ]
        )

    output = tmp_path / "report"
    summary = evaluate(truth, output)

    assert summary["documents_total"] == 1
    assert summary["documents_accepted"] == 1
    assert summary["selected_record_coverage"] == 1.0
    assert summary["verified_exact_match_precision"] == 1.0
    assert summary["verified_exact_match_recall"] == 1.0
    assert summary["false_verified_count"] == 0
    assert summary["missing_routing_accuracy"] == 1.0
    assert (output / "summary.json").exists()
    assert "Metrics come only" in (output / "report.md").read_text(encoding="utf-8")
