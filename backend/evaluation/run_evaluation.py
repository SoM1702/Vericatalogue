from __future__ import annotations

import argparse
import csv
import json
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from app.extraction import FIELD_ORDER, SourceReadError, parse_source_payload
from app.normalization import normalize_value, normalized_key
from app.repository import ProductRepository
from app.service import CatalogService


REQUIRED_COLUMNS = {"case_id", "source_path", "record_index", "field", "expected_value", "expected_status"}
ALLOWED_STATUSES = {"verified", "inferred", "missing", "conflict"}


@dataclass(frozen=True)
class GroundTruthField:
    case_id: str
    source_path: Path
    record_index: int
    field: str
    expected_value: str
    expected_status: str


def _canonical_marker(field: str, value: str | None) -> str:
    if not value:
        return ""
    normalized, _ = normalize_value(field, value)
    return normalized_key(normalized) or " ".join(value.casefold().split())


def read_ground_truth(path: Path) -> list[GroundTruthField]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            missing = ", ".join(sorted(REQUIRED_COLUMNS.difference(reader.fieldnames or [])))
            raise ValueError(f"Ground truth is missing required column(s): {missing}.")
        fields: list[GroundTruthField] = []
        for line_number, row in enumerate(reader, start=2):
            field = (row.get("field") or "").strip()
            status = (row.get("expected_status") or "").strip().lower()
            source_value = (row.get("source_path") or "").strip()
            if field not in FIELD_ORDER:
                raise ValueError(f"Ground-truth row {line_number} has unsupported field '{field}'.")
            if status not in ALLOWED_STATUSES:
                raise ValueError(f"Ground-truth row {line_number} has unsupported expected_status '{status}'.")
            if not source_value:
                raise ValueError(f"Ground-truth row {line_number} needs a source_path.")
            try:
                record_index = int(row.get("record_index") or "0")
            except ValueError as exc:
                raise ValueError(f"Ground-truth row {line_number} has an invalid record_index.") from exc
            if record_index < 0:
                raise ValueError(f"Ground-truth row {line_number} has a negative record_index.")
            source_path = Path(source_value)
            if not source_path.is_absolute():
                source_path = (path.parent / source_path).resolve()
            fields.append(
                GroundTruthField(
                    case_id=(row.get("case_id") or "").strip() or f"row-{line_number}",
                    source_path=source_path,
                    record_index=record_index,
                    field=field,
                    expected_value=(row.get("expected_value") or "").strip(),
                    expected_status=status,
                )
            )
    if not fields:
        raise ValueError("Ground truth has no evaluation rows.")
    return fields


def _result_status(expected: GroundTruthField, predicted_status: str, exact_match: bool) -> str:
    if expected.expected_status == "missing":
        return "pass" if predicted_status == "missing" else "fail"
    if expected.expected_status == "conflict":
        return "pass" if predicted_status == "conflict" else "fail"
    return "pass" if predicted_status == expected.expected_status and exact_match else "fail"


def evaluate(ground_truth_path: Path, output_directory: Path) -> dict:
    """Evaluate parser output against a locked, local ground-truth CSV.

    Sources are read directly from the declared paths and are never copied into the
    app upload folder. The caller is responsible for permission to use every source.
    """
    expectations = read_ground_truth(ground_truth_path)
    output_directory.mkdir(parents=True, exist_ok=True)
    groups: dict[tuple[str, Path, int], list[GroundTruthField]] = defaultdict(list)
    for expectation in expectations:
        groups[(expectation.case_id, expectation.source_path, expectation.record_index)].append(expectation)

    parser_cache: dict[Path, list] = {}
    document_errors: dict[Path, str] = {}
    results: list[dict] = []
    accepted_documents: set[Path] = set()
    selected_records = 0
    with tempfile.TemporaryDirectory(prefix="vericatalog-evaluation-") as directory:
        service = CatalogService(ProductRepository(Path(directory) / "evaluation.sqlite3"))
        for (case_id, source_path, record_index), expected_fields in groups.items():
            if source_path not in parser_cache and source_path not in document_errors:
                try:
                    parser_cache[source_path] = parse_source_payload(source_path.name, source_path.read_bytes())
                    accepted_documents.add(source_path)
                except (OSError, SourceReadError) as exc:
                    document_errors[source_path] = str(exc)
            source_rows = parser_cache.get(source_path, [])
            if record_index < len(source_rows):
                selected_records += 1
                attributes = {attribute.field: attribute for attribute in service.build_product([source_rows[record_index]]).attributes}
            else:
                attributes = {}
            for expected in expected_fields:
                actual = attributes.get(expected.field)
                predicted_status = actual.status if actual else "missing"
                predicted_value = (
                    actual.reviewed_value
                    or (actual.normalized_value.display if actual and actual.normalized_value else actual.raw_value if actual else "")
                )
                exact_match = _canonical_marker(expected.field, expected.expected_value) == _canonical_marker(expected.field, predicted_value)
                results.append(
                    {
                        "case_id": case_id,
                        "source_path": str(source_path),
                        "record_index": record_index,
                        "field": expected.field,
                        "expected_value": expected.expected_value,
                        "expected_status": expected.expected_status,
                        "predicted_value": predicted_value,
                        "predicted_status": predicted_status,
                        "exact_match": exact_match,
                        "evidence_count": len(actual.evidence) if actual else 0,
                        "result": _result_status(expected, predicted_status, exact_match),
                        "parser_error": document_errors.get(source_path, ""),
                    }
                )

    direct_expected = [row for row in results if row["expected_status"] == "verified"]
    inferred_expected = [row for row in results if row["expected_status"] == "inferred"]
    predicted_verified = [row for row in results if row["predicted_status"] == "verified"]
    correct_verified = [
        row for row in results if row["expected_status"] == "verified" and row["predicted_status"] == "verified" and row["exact_match"]
    ]
    correct_inferred = [
        row for row in results if row["expected_status"] == "inferred" and row["predicted_status"] == "inferred" and row["exact_match"]
    ]
    false_verified = [row for row in predicted_verified if row not in correct_verified]
    missing_expected = [row for row in results if row["expected_status"] == "missing"]
    conflict_expected = [row for row in results if row["expected_status"] == "conflict"]
    documents = {expectation.source_path for expectation in expectations}
    summary = {
        "measurement_boundary": "Metrics come only from this locked ground-truth file. They are not a general real-world accuracy claim.",
        "documents_total": len(documents),
        "documents_accepted": len(accepted_documents),
        "document_acceptance_rate": round(len(accepted_documents) / len(documents), 4) if documents else 0.0,
        "selected_records_total": len(groups),
        "selected_records_covered": selected_records,
        "selected_record_coverage": round(selected_records / len(groups), 4) if groups else 0.0,
        "ground_truth_field_rows": len(results),
        "verified_exact_match_precision": round(len(correct_verified) / len(predicted_verified), 4) if predicted_verified else None,
        "verified_exact_match_recall": round(len(correct_verified) / len(direct_expected), 4) if direct_expected else None,
        "inferred_candidate_exact_match_rate": round(len(correct_inferred) / len(inferred_expected), 4) if inferred_expected else None,
        "false_verified_count": len(false_verified),
        "false_verified_rate": round(len(false_verified) / len(predicted_verified), 4) if predicted_verified else 0.0,
        "missing_routing_accuracy": round(
            sum(row["predicted_status"] == "missing" for row in missing_expected) / len(missing_expected), 4
        ) if missing_expected else None,
        "conflict_routing_accuracy": round(
            sum(row["predicted_status"] == "conflict" for row in conflict_expected) / len(conflict_expected), 4
        ) if conflict_expected else None,
        "pass_count": sum(row["result"] == "pass" for row in results),
        "fail_count": sum(row["result"] == "fail" for row in results),
        "document_errors": {str(path): error for path, error in document_errors.items()},
    }
    _write_results(output_directory / "field_results.csv", results)
    (output_directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output_directory / "report.md").write_text(_report_markdown(summary), encoding="utf-8")
    return summary


def _write_results(path: Path, results: list[dict]) -> None:
    columns = [
        "case_id", "source_path", "record_index", "field", "expected_value", "expected_status", "predicted_value",
        "predicted_status", "exact_match", "evidence_count", "result", "parser_error",
    ]
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)


def _report_markdown(summary: dict) -> str:
    lines = ["# VeriCatalog Proof Evaluation Report", "", summary["measurement_boundary"], "", "| Measure | Result |", "| --- | --- |"]
    labels = {
        "documents_total": "Documents in ground truth",
        "documents_accepted": "Documents accepted",
        "document_acceptance_rate": "Document acceptance rate",
        "selected_records_covered": "Selected records covered",
        "selected_record_coverage": "Selected record coverage",
        "verified_exact_match_precision": "Verified exact-match precision",
        "verified_exact_match_recall": "Verified exact-match recall",
        "inferred_candidate_exact_match_rate": "Inferred candidate exact-match rate",
        "false_verified_count": "False-Verified count",
        "false_verified_rate": "False-Verified rate",
        "missing_routing_accuracy": "Missing routing accuracy",
        "conflict_routing_accuracy": "Conflict routing accuracy",
        "pass_count": "Passing field checks",
        "fail_count": "Failing field checks",
    }
    for key, label in labels.items():
        lines.append(f"| {label} | {summary.get(key)} |")
    lines.extend(["", "See `field_results.csv` for each individual field comparison.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate VeriCatalog Proof against authorised local source documents.")
    parser.add_argument("ground_truth", type=Path, help="CSV with one expected field per row.")
    parser.add_argument("--output", type=Path, required=True, help="Directory for summary JSON, report Markdown, and field results CSV.")
    args = parser.parse_args()
    summary = evaluate(args.ground_truth.resolve(), args.output.resolve())
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
