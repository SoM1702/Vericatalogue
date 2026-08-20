# Implementation Plan

## Milestone 1: Foundation
- **Tasks**: Clean project setup, backend FastAPI health endpoint, frontend React/Vite shell, sample synthetic valve data (PDF/CSV), and local README.
- **Acceptance**: App builds and runs locally via a single command (or separate FE/BE dev scripts).

## Milestone 2: Extraction and Schema
- **Tasks**: Upload API, text/page evidence extraction via `PyMuPDF`/`pdfplumber`, map data into Pydantic schema, preserve raw values, implement unit normalization using `Pint`.
- **Acceptance**: Can upload a PDF and get a parsed structured response back containing raw, normalized, and evidence fields.

## Milestone 3: Validation and Review Workbench
- **Tasks**: Deterministic validation rules, conflict/missing field detection, UI for Evidence Workbench (side-by-side view, tags), and Approval/Rejection logic.
- **Acceptance**: UI shows color-coded tags for Verified/Inferred/Missing/Conflict. User can click a field, see the exact text snippet, and approve or edit the value.

## Milestone 4: Export and Catalog Health
- **Tasks**: JSON/CSV export endpoints, batch processing logic for CSVs, Catalog Health UI dashboard with metrics and filtering.
- **Acceptance**: User can process a batch of 50 synthetic items and view aggregated stats, then download the review queue.

## Milestone 5: Quality and Handoff
- **Tasks**: Pytest suite for backend logic (normalization, validation, exports), UI polish, accessible labels, complete `FINAL_SUBMISSION_CHECKLIST.md`.
- **Acceptance**: All tests pass. UI looks premium and handles empty/error states cleanly. Handoff document generated.

**Optional AI acceptance:** With no `.env`, deterministic mode works without a key. With a valid local provider configuration, candidate mapping remains server-side, checks source quotes independently, and never converts AI-only output to `Verified`.

## Milestone 6: Bounded Evidence Review Agent
- **Tasks**: Run deterministic inspect-only exception, provenance, validation, and task-ranking tools after enrichment; persist the plan and trace; expose it in the Workbench; prevent product mutations by the agent.
- **Acceptance**: A conflict run shows a ranked human task with retained evidence references and four recorded tools. Automated tests verify conflict-first ranking, plan persistence, and no mutation of values or review state.

## Milestone 7: Competition Readiness
- **Tasks**: Add conservative multi-SKU PDF row/card segmentation, a review-selectable record path, a reusable external-ground-truth evaluation harness, visible grounded-AI result reporting, API journey tests, and a recorded local-demo fallback.
- **Acceptance**: Segmented records never mix SKU evidence; the evaluator reports field-level outcomes rather than a vague accuracy claim; the AI-disabled path remains fully usable; and a fresh clone can run the documented demo.

## Risks, Assumptions, and Fallbacks
| Risk / assumption | Fallback |
| --- | --- |
| PDF layouts vary or are image-only. | Read embedded text and table-like pairs; attempt local Tesseract OCR only on low-text pages; retain document-level cues as Inferred and reject sources with no valve/fitting context. |
| XLSX engines vary across local machines. | Read simple header-row worksheets with a dependency-light parser; return a useful error for complex workbooks. |
| Pattern mapping misses an unfamiliar supplier label. | Preserve the source text, use Missing/Inference rather than fabricated verification, and allow reviewer edit. |
| Local port or virtual-environment setup differs. | Document separate frontend/backend commands and port overrides in the README. |
| Time is constrained. | Prioritize the PDF happy path, deliberate conflict, evidence review, exports, and 50+ batch health over broad category support. |
