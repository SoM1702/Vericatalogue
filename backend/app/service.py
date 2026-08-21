from __future__ import annotations

import csv
import io
import uuid
from collections import Counter

from .extraction import FIELD_ORDER, Candidate, SourceRow
from .models import Evidence, NormalizedValue, ProductAttribute, ProductRecord, ReviewAgentPlan, ReviewRequest, ValidationResult
from .normalization import infer_product_type, normalize_value, normalized_key
from .repository import ProductRepository
from .review_agent import EvidenceReviewAgent


REQUIRED_FIELDS = {
    "manufacturer",
    "manufacturer_part_number",
    "product_type",
    "material",
    "size",
    "end_connection",
    "pressure_rating",
}


def _attribute_map(product: ProductRecord) -> dict[str, ProductAttribute]:
    return {attribute.field: attribute for attribute in product.attributes}


def _unique_candidates(candidates: list[Candidate]) -> list[tuple[Candidate, NormalizedValue | None, str | None]]:
    output: list[tuple[Candidate, NormalizedValue | None, str | None]] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized, explanation = normalize_value("", candidate.raw_value)
        marker = candidate.raw_value.strip().lower()
        if marker not in seen:
            output.append((candidate, normalized, explanation))
            seen.add(marker)
    return output


class CatalogService:
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def build_product(self, source_rows: list[SourceRow]) -> ProductRecord:
        candidates_by_field: dict[str, list[Candidate]] = {field: [] for field in FIELD_ORDER}
        for source_row in source_rows:
            for field, candidates in source_row.candidates.items():
                if field in candidates_by_field:
                    candidates_by_field[field].extend(candidates)

        attributes: list[ProductAttribute] = []
        title_candidates = candidates_by_field["product_title"]
        for field in FIELD_ORDER:
            candidates = candidates_by_field[field]
            inferred = bool(candidates) and all(candidate.inferred for candidate in candidates)
            if not candidates and field == "product_type" and title_candidates:
                inferred_type = infer_product_type(title_candidates[0].raw_value)
                if inferred_type:
                    title_evidence = title_candidates[0].evidence
                    candidates = [
                        Candidate(
                            inferred_type,
                            Evidence(
                                source_file=title_evidence.source_file,
                                page=title_evidence.page,
                                row=title_evidence.row,
                                snippet=title_evidence.snippet,
                                method="deterministic_title_inference",
                            ),
                            inferred=True,
                        )
                    ]
                    inferred = True

            if not candidates:
                attributes.append(
                    ProductAttribute(
                        field=field,
                        status="missing",
                        confidence=0.0,
                        validation_results=self._validation_for_missing(field),
                    )
                )
                continue

            normalized_candidates: list[tuple[Candidate, NormalizedValue | None, str | None]] = []
            value_markers: set[str] = set()
            for candidate in candidates:
                normalized, explanation = normalize_value(field, candidate.raw_value)
                marker = normalized_key(normalized) or candidate.raw_value.strip().lower()
                normalized_candidates.append((candidate, normalized, explanation))
                value_markers.add(marker)

            first, normalized, explanation = normalized_candidates[0]
            status = "inferred" if inferred else "verified"
            if len(value_markers) > 1:
                status = "conflict"
            validations = self._validation_for_value(field, normalized, first.raw_value, candidates_by_field)
            if any(item.status == "fail" for item in validations):
                status = "conflict"
            if status == "conflict" and len(value_markers) > 1:
                validations.append(
                    ValidationResult(
                        rule="cross_source_consistency",
                        status="fail",
                        message="Sources provide different normalized values; human review is required.",
                    )
                )
            confidence = self._confidence(status, explanation, validations)
            attributes.append(
                ProductAttribute(
                    field=field,
                    raw_value=first.raw_value,
                    normalized_value=normalized,
                    normalization_explanation=explanation,
                    status=status,
                    confidence=confidence,
                    evidence=[candidate.evidence for candidate, _, _ in normalized_candidates],
                    validation_results=validations,
                )
            )

        source_kinds = {source.source_kind for source in source_rows}
        source_kind = "synthetic_demo" if source_kinds == {"synthetic_demo"} else "manual" if source_kinds == {"manual"} else "uploaded"
        return ProductRecord(id=f"vp_{uuid.uuid4().hex[:12]}", source_kind=source_kind, attributes=attributes)

    def enrich(self, source_rows: list[SourceRow]) -> ProductRecord:
        product = self.build_product(source_rows)
        self.repository.save(product)
        self.run_review_agent(product.id)
        return self.repository.get(product.id) or product

    def batch(self, source_rows: list[SourceRow]) -> list[ProductRecord]:
        products = []
        for source_row in source_rows:
            product = self.build_product([source_row])
            self.repository.save(product)
            self.run_review_agent(product.id)
            refetched = self.repository.get(product.id)
            products.append(refetched or product)
        return products

    def review(self, product_id: str, field: str, request: ReviewRequest) -> ProductRecord | None:
        product = self.repository.get(product_id)
        if not product:
            return None
        attribute = next((item for item in product.attributes if item.field == field), None)
        if not attribute:
            return None
        if request.action == "edit" and not request.value:
            raise ValueError("An edited review needs a value.")
        attribute.review_status = {"approve": "approved", "reject": "rejected", "edit": "edited"}[request.action]
        attribute.review_note = request.note
        if request.action == "edit":
            attribute.reviewed_value = request.value
        self.repository.save(product)
        self.repository.add_audit_event(product_id, field, request.action, request.note)
        return product

    def run_review_agent(self, product_id: str) -> ReviewAgentPlan | None:
        product = self.repository.get(product_id)
        if not product:
            return None
            
        # Collect past human review corrections (Feedback/Learning loop)
        historical_corrections = []
        try:
            for p in self.repository.list():
                for attr in p.attributes:
                    if attr.review_status == "edited" and attr.reviewed_value:
                        historical_corrections.append({
                            "field": attr.field,
                            "raw_value": attr.raw_value,
                            "reviewed_value": attr.reviewed_value
                        })
                    elif attr.review_status == "approved" and attr.normalized_value:
                        historical_corrections.append({
                            "field": attr.field,
                            "raw_value": attr.raw_value,
                            "reviewed_value": attr.normalized_value.display
                        })
        except Exception:
            pass

        plan, updated_attributes, decisions = EvidenceReviewAgent().run_with_updates(product, historical_corrections)
        
        # Save every agent action decision to the SQLite database
        for decision in decisions:
            self.repository.save_agent_decision(decision)

        product.attributes = updated_attributes
        self.repository.save(product)
        return self.repository.save_review_agent_run(plan)


    def product_csv(self, product: ProductRecord) -> str:
        values = _attribute_map(product)
        header = ["product_id", "category", *FIELD_ORDER]
        row = [product.id, product.category]
        for field in FIELD_ORDER:
            attribute = values[field]
            row.append(attribute.reviewed_value or (attribute.normalized_value.display if attribute.normalized_value else ""))
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)
        writer.writerow(row)
        return output.getvalue()

    def review_queue_csv(self, products: list[ProductRecord]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["product_id", "manufacturer_part_number", "product_title", "priority", "reasons"])
        for priority in self.health_metrics(products)["priority_products"]:
            writer.writerow(
                [priority["product_id"], priority["manufacturer_part_number"], priority["product_title"], priority["priority"], "; ".join(priority["reasons"])]
            )
        return output.getvalue()

    def health_metrics(self, products: list[ProductRecord]) -> dict:
        all_attributes = [attribute for product in products for attribute in product.attributes]
        required_attributes = [attribute for product in products for attribute in product.attributes if attribute.field in REQUIRED_FIELDS]
        verified_required = sum(attribute.status == "verified" for attribute in required_attributes)
        field_review_count = sum(attribute.status in {"inferred", "missing", "conflict"} for attribute in all_attributes)
        conflicts = sum(attribute.status == "conflict" for attribute in all_attributes)
        missing_required = sum(attribute.status == "missing" for attribute in required_attributes)

        keys = []
        priority_products = []
        for product in products:
            values = _attribute_map(product)
            mpn = values["manufacturer_part_number"].normalized_value
            manufacturer = values["manufacturer"].normalized_value
            title = values["product_title"].normalized_value
            size = values["size"].normalized_value
            if mpn and mpn.value:
                key = f"mpn::{normalized_key(mpn)}"
            else:
                key = "fallback::" + "|".join(filter(None, [normalized_key(manufacturer), normalized_key(title), normalized_key(size)]))
            if key and key != "fallback::":
                keys.append(key)

            reasons: list[str] = []
            priority = 0
            for attribute in product.attributes:
                if attribute.status == "conflict":
                    priority += 100
                    reasons.append(f"Conflicting {attribute.field.replace('_', ' ')}")
                elif attribute.status == "missing" and attribute.field in REQUIRED_FIELDS:
                    priority += 80
                    reasons.append(f"Missing required {attribute.field.replace('_', ' ')}")
                elif attribute.status == "inferred":
                    priority += 55
                    reasons.append(f"Inferred {attribute.field.replace('_', ' ')}")
            if priority:
                priority_products.append(
                    {
                        "product_id": product.id,
                        "manufacturer_part_number": mpn.display if mpn else "—",
                        "product_title": title.display if title else "Untitled product",
                        "priority": priority,
                        "reasons": reasons,
                        "statuses": sorted({attribute.status for attribute in product.attributes if attribute.status != "verified"}),
                    }
                )
        duplicate_keys = {key for key, count in Counter(keys).items() if count > 1}
        return {
            "product_count": len(products),
            "completeness_score": round((verified_required / len(required_attributes) * 100) if required_attributes else 0, 1),
            "fields_requiring_review": field_review_count,
            "conflict_count": conflicts,
            "missing_mandatory_fields": missing_required,
            "duplicate_candidate_count": len(duplicate_keys),
            "priority_products": sorted(priority_products, key=lambda item: item["priority"], reverse=True)[:20],
            "metric_note": "Completeness is the percentage of required field instances marked Verified. Metrics describe the processed batch only.",
        }

    @staticmethod
    def _validation_for_missing(field: str) -> list[ValidationResult]:
        if field in REQUIRED_FIELDS:
            return [ValidationResult(rule="required_field", status="fail", message="Required for a PIM-ready valve/fitting record.")]
        return [ValidationResult(rule="optional_field", status="warning", message="No source evidence was found for this optional field.")]

    @staticmethod
    def _validation_for_value(
        field: str,
        normalized: NormalizedValue | None,
        raw_value: str,
        candidates_by_field: dict[str, list[Candidate]],
    ) -> list[ValidationResult]:
        validations: list[ValidationResult] = [
            ValidationResult(
                rule="required_field" if field in REQUIRED_FIELDS else "source_evidence_present",
                status="pass",
                message="Direct source evidence is retained for this value.",
            )
        ]
        if field in {"size", "pressure_rating", "temperature_range"}:
            validations.append(
                ValidationResult(
                    rule="value_and_unit_parse",
                    status="pass" if normalized else "fail",
                    message="Recognized numeric value and compatible unit." if normalized else "Value or unit could not be parsed.",
                )
            )
        if field == "size" and normalized and isinstance(normalized.value, (int, float)) and normalized.value <= 0:
            validations.append(ValidationResult(rule="positive_size", status="fail", message="Size must be positive."))
        if field == "pressure_rating" and normalized and isinstance(normalized.value, (int, float)):
            materials = candidates_by_field.get("material", [])
            types = candidates_by_field.get("product_type", [])
            material_raw = materials[0].raw_value.lower() if materials else ""
            type_raw = types[0].raw_value.lower() if types else ""
            if "brass" in material_raw and "ball" in type_raw and normalized.unit == "WOG" and normalized.value > 1000:
                validations.append(
                    ValidationResult(
                        rule="brass_ball_valve_pressure_plausibility",
                        status="fail",
                        message="Brass ball valve pressure above 1,000 WOG requires review.",
                    )
                )
        return validations

    @staticmethod
    def _confidence(status: str, explanation: str | None, validations: list[ValidationResult]) -> float:
        if status == "missing":
            return 0.0
        if status == "conflict" or any(item.status == "fail" for item in validations):
            return 0.25
        if status == "inferred":
            return 0.55
        return 0.90 if explanation else 0.95
