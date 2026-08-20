# Final Submission Checklist

## Functional MVP

- [x] Local web app implements Enrich Product, Evidence & Review Workbench, and Catalog Health.
- [x] Embedded-text/table-like PDF, local OCR when Tesseract is installed, CSV, simple XLSX, and manual partial-entry source paths are implemented with useful errors.
- [x] Synthetic PDF produces a complete valve record with page-level source evidence.
- [x] Size, material, pressure, and temperature normalization preserve raw values and explain canonical values.
- [x] Verified, Inferred, Missing, and Conflict statuses are explicit and do not rely only on colour.
- [x] Deliberate `600 WOG`/`400 WOG` cross-source conflict keeps both evidence snippets and requires review.
- [x] Approve, reject, and edit actions persist locally without erasing original evidence.
- [x] JSON/CSV product exports and review-queue CSV export are available.
- [x] 60-row synthetic batch calculates product count, completeness, fields requiring review, conflicts, missing mandatory fields, duplicate candidates, and priority rows.
- [x] Bounded Evidence Review Agent runs four inspect-only local tools, persists an auditable plan, ranks exception fields, and cannot mutate, approve, resolve, or export a product.
- [x] Clearly repeated PDF product cards and explicit catalog table rows are kept as separate records; the reviewer chooses an SKU rather than silently merging neighboring values.

## Quality verification

- [x] Backend automated tests cover normalization, required fields, conflict detection, evidence persistence, exports, PDF text/table-layout/OCR/multi-SKU input, API journeys, batch input, optional-AI grounding/inference safeguards, evaluation-output safeguards, and Review Agent prioritisation/persistence/non-mutation safeguards.
- [x] A local authorised-data evaluation harness produces auditable field-level results without copying external sources into the project.
- [ ] Run the evaluator on an authorised, independently labelled real-world source set and report its source scope with the field-level measures. No general accuracy number is currently claimed.
- [x] Frontend TypeScript production build and lint pass.
- [x] Live local QA completed for PDF enrichment, conflict review, review persistence, and catalog-health batch flow.
- [x] Empty, error, processing, and responsive UI states are provided.

## Submission materials

- [x] Complete English README with local commands and demo path.
- [x] Product requirements, compliance, scope, flows, schema, architecture, evaluation, demo, deck outline, decisions, and implementation plan are in `docs/`.
- [x] Seven-slide pitch-deck content is in `docs/09-pitch-deck-outline.md`.
- [x] Rendered, editable seven-slide deck is in `submission/VeriCatalog-Proof-UniHack-2026.pptx` and passed slide overflow checks.
- [x] Validated 90-second silent demo-video source and scene snapshots are in `videos/vericatalog-proof-demo/`; runtime, layout, motion, and 47/47 text contrast checks pass.
- [x] Ready-to-paste solution description is in `docs/SUBMISSION_DESCRIPTION.md`.
- [x] Data provenance is recorded in `docs/DATA_SOURCES.md`; all shipped demo data is synthetic.
- [x] Synthetic single-SKU, conflict, batch, and multi-SKU demo files are generated locally and explicitly labelled as non-real data.
- [ ] Add the repository URL after the owner publishes the source repository.
- [ ] If the event accepts a product video, owner approves the final render, reviews the MP4, and uploads it.
- [ ] Owner submits through the official event workflow. This project does not register, publish, or submit externally.
