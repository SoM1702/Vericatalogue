# Architectural and Product Decisions

## 1. Local-First Architecture
**Decision**: Use SQLite and local file processing instead of cloud databases and object storage.
**Reason**: Hackathon rules stipulate no cloud accounts, credentials, or external dependencies where possible. A local setup ensures judges can run the repo instantly.

## 2. Evidence Over AI Hallucination
**Decision**: The system will NOT silently fill missing values or invent data. All extraction must be tied to a source snippet.
**Reason**: The core value proposition of "VeriCatalog Proof" is trust. Industrial commerce relies on accurate specifications. If we cannot prove where a value came from, it is marked as `Missing` or `Inferred` (requiring human review).

## 3. Tech Stack
**Decision**: React + Vite + Tailwind CSS for Frontend. FastAPI + Python for Backend.
**Reason**: Python has the best ecosystem for PDF extraction (`PyMuPDF`) and unit conversion (`Pint`). FastAPI works perfectly with Pydantic for schema validation. React/Tailwind allows for rapid, premium UI development.

## 4. Extraction Method
**Decision**: For the MVP, we will use regex/heuristic text extraction mixed with a small deterministic local AI mapping (or mock LLM) to link text snippets to the PIM schema.
**Reason**: Keeps the demo fast, reliable, and free of API key requirements.

## 5. Scope Constriction
**Decision**: Focus entirely on Industrial Valves and Fittings.
**Reason**: Prevents the MVP from being a shallow "works for anything but badly" tool. Valves have complex units (pressure, temperature, diameter) which perfectly demonstrate the normalization and conflict engine.

## 6. Existing Stack Preservation
**Decision**: Retain the existing React 19 + TypeScript + Vite + Tailwind frontend and the prepared local Python environment.
**Reason**: The frontend starter is a viable foundation, and the virtual environment already includes FastAPI, Pydantic, Pint, PyMuPDF, pytest, and other required local tooling.

## 7. Confidence Is a Review Heuristic
**Decision**: Display confidence only as a documented deterministic review heuristic, never as model accuracy or a probability.
**Reason**: The MVP is evidence-first and has no labelled real-world benchmark. The formula and its limitations are documented in `docs/05-data-schema-and-validation.md`.

## 8. Demo Data Provenance
**Decision**: Commit only clearly labelled synthetic supplier documents and batch data for the MVP.
**Reason**: No authorized real supplier catalog is present. Synthetic assets make the demo reproducible without implying use of a real manufacturer’s data.

## 9. Bounded Evidence Review Agent, Not an Open-Ended Agent Framework
**Decision**: Add a local, deterministic Review Agent with four inspect-only tools rather than introducing LangGraph or an autonomous LLM loop.
**Reason**: The useful problem is prioritising evidence-backed human review, not generating product facts. A fixed tool sequence can inspect exceptions, provenance, and validation results; persist an auditable ranking; and remain reproducible without an API key. The agent has no mutation, approval, export, browser, shell, network, or model-invocation tools, so it cannot alter a product record or turn a heuristic into an ungrounded decision.

## 10. Conservative Multi-SKU PDF Segmentation
**Decision**: Split only explicitly repeated labelled product cards and explicit table rows into separate source records, then require the user to select one before enrichment.
**Reason**: Industrial catalog PDFs often place multiple SKUs on one page. Merging nearby rows would be a worse failure than returning a partial record. Ambiguous manuals therefore retain their safe partial-document behaviour instead of claiming a product boundary that is not demonstrable.

## 11. External, Locked Accuracy Evaluation
**Decision**: Ship an evaluator and a ground-truth schema, but no bundled “accuracy” score or unauthorised real documents.
**Reason**: Synthetic fixtures validate deterministic behaviour but cannot establish performance on supplier catalogs. The evaluator reads a team-authorised, independently checked source set in place and records field-level precision/recall and safe-routing measures with the source scope, avoiding a misleading universal metric.
