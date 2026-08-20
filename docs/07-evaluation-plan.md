# Evaluation Plan

## Automated Tests
- **Unit Normalization**: Test conversions (mm to inches, Celsius to Fahrenheit).
- **Required Fields**: Ensure empty critical fields are flagged as `Missing`.
- **Conflict Detection**: Supply mock data with conflicting pressure ratings and verify it results in a `Conflict` status.
- **Evidence Persistence**: Verify that the exact text snippet and source file name are retained in the Pydantic schema output.
- **Exports**: Ensure JSON and CSV generation endpoints return valid, parseable files.
- **Optional AI guardrail**: Discard candidate values whose raw text or quoted snippet is absent from the source; retain AI-only fields as `Inferred`, never `Verified`.
- **PDF layout/OCR guardrails**: Test table-like label/value pairs, scanned-PDF local OCR when Tesseract is installed, global unit notation (`DN`, `PN`, ASME class), and an unrelated document that must still fail safely.
- **Review Agent guardrails**: Verify its four-tool trace, conflict-first prioritisation, evidence count, persistence, and the invariant that running it does not mutate a field value or review status.
- **Multi-SKU isolation**: Verify repeated, explicitly-labelled product cards and explicit catalog-table rows become separate parser records, and that API selection never merges fields across them.
- **API journey**: Exercise upload, multi-SKU selection, review persistence, export, demo input, and batch processing through the FastAPI ASGI boundary.

## Manual Scenarios
1. **Happy Path**: Upload a clean synthetic PDF for a Ball Valve. Verify all fields are extracted, normalized correctly, and marked `Verified` with proper evidence snippets.
2. **Conflict Scenario**: Upload a PDF and a CSV for the same product with differing materials (e.g., Brass vs Stainless Steel). Verify the UI highlights this conflict in the Workbench.
3. **Missing Data**: Upload a PDF that does not contain a Pressure Rating. Verify the field is marked `Missing`, not hallucinated by the system.
4. **Batch Upload**: Upload a CSV of 50 synthetic products. Check the Catalog Health dashboard to ensure accurate aggregate statistics and review queues.
5. **Bounded Review Agent**: Upload the deliberate conflict pair, run the agent from the Workbench, and confirm it ranks conflict tasks, surfaces retained evidence references, records four local checks, and asks for human approval rather than making a change.

## Metric Definitions and Limits
- `completeness_score = verified required fields / required fields × 100` across processed products. A conflict is not complete.
- `fields_requiring_review` counts fields in `Inferred`, `Missing`, or `Conflict` status, plus explicitly non-pending review states when displayed.
- `duplicate_candidate_count` counts normalized identifier keys occurring more than once: part number first, otherwise manufacturer + title + size.
- These metrics are properties of the processed batch, not accuracy, time-saving, ROI, or supplier-quality claims.

The synthetic demo set is designed to exercise rules and cannot estimate real-world accuracy. The repository now includes the local evaluator in `backend/evaluation/`; it requires an authorized labelled source set, published inclusion criteria, field-level precision/recall method, and known limitations. It emits document acceptance, selected-record coverage, verified exact-match precision/recall, false-Verified rate, and missing/conflict routing measures from the locked ground truth. It must not be reported as an overall accuracy claim.

The Review Agent is evaluated for safe triage behaviour and traceability, not for accuracy. It consumes already-extracted data and does not generate or change an attribute.
