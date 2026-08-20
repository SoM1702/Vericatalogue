# VeriCatalog Proof

**Evidence-First Product Intelligence for Industrial Commerce**

VeriCatalog Proof is a local hackathon MVP for industrial valves and fittings. It turns a supplier PDF, CSV, XLSX, or manual partial entry into a PIM-ready product record while preserving the raw value, source snippet, source location, normalization explanation, validation result, truth status, and human review state for every field.

It is deliberately not a generic chat, RAG, product-copy generator, or production PIM integration. Its job is to make catalog attributes auditable before export.

## What the MVP demonstrates

- Three focused screens: **Enrich Product**, **Evidence & Review Workbench**, and **Catalog Health**
- Embedded-text and table-like PDFs, locally OCR-processed scanned pages when Tesseract is installed, CSV, simple XLSX, and manual partial-entry processing
- Conservative multi-SKU PDF segmentation: clearly repeated product cards and explicit table rows stay separate, and the reviewer selects the record to enrich
- Page-level PDF and row-level table evidence
- Deterministic normalization for metric/imperial size, material aliases, pressure notation, and temperature ranges
- Verified, Inferred, Missing, and Conflict truth statuses
- Required-field, type/unit, plausibility, cross-source conflict, and duplicate-candidate checks
- Approve, reject, and edit review actions persisted in local SQLite
- A bounded local **Evidence Review Agent** that inspects exceptions, provenance, and validation output; ranks human review tasks; and records its tool trace without changing any product value
- PIM-ready JSON/CSV product export and review-queue export
- A generated synthetic text PDF, deliberate conflicting CSV, and 60-row batch—all clearly labelled as synthetic

## Local setup

Prerequisites: Node.js 20+ and Python 3.11+ (the provided `backend/venv` already contains the needed local packages in this workspace).

Terminal 1 — backend:

```bash
cd /Users/nan/Documents/codes/unihack/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

If starting from a fresh environment instead of the supplied virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Terminal 2 — frontend:

```bash
cd /Users/nan/Documents/codes/unihack/frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

If port 8000 is in use, pick another local API port and create `frontend/.env.local`:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8010
```

Then run the backend with `--port 8010`. `.env.example` lists the local-only server defaults. No API key, model credential, database server, or cloud account is required.

## Optional AI candidate mapping

The deterministic extractor is the default demo mode. To add your own OpenAI-compatible AI provider without exposing its key to the browser:

```bash
cd /Users/nan/Documents/codes/unihack
cp backend/.env.example backend/.env
```

Edit `backend/.env` with your provider details:

```bash
VERICATALOG_AI_ENABLED=true
VERICATALOG_AI_API_KEY=your_key_here
VERICATALOG_AI_BASE_URL=https://your-provider.example/v1/chat/completions
VERICATALOG_AI_MODEL=your-model-id
```

Restart the backend. The UI then displays **AI candidate mapper**. The mapper can only add a value when its raw value and quoted snippet both occur in the uploaded source; its fields are always labelled **Inferred** and require review. A key never enters frontend code, browser storage, exports, logs, or version control. Keep `VERICATALOG_AI_BATCH_LIMIT=10` unless you intentionally want more provider calls for a batch.

## Bounded Evidence Review Agent

After opening a record in **Evidence & Review Workbench**, choose **Run review agent**. It runs four named, local inspection tools in a fixed bounded sequence: identify exception fields, inspect retained provenance, evaluate validation output, and rank human actions. The resulting plan and tool trace are stored in SQLite so the reviewer can see why each task was prioritised.

This is intentionally an evidence-first agentic workflow, not an autonomous decision maker: it has no browser, shell, export, database-write, approval, or field-edit tools. It cannot invent facts, resolve a conflict, approve a field, or call an external model. It improves the review queue and demo story; it does **not** raise or claim extraction accuracy.

## PDF intake boundaries

The PDF path first reads embedded text, then recognises explicit labels and table-like label/value pairs. It can also use locally installed Tesseract OCR for low-text scanned pages; no page image leaves the machine. A document-level heading or manufacturer cue may create an **Inferred** partial record for human review, but the app never upgrades that inference to `Verified` or invents a missing product specification. Clearly repeated product cards and explicit catalog table rows are returned as separate records; the UI requires the reviewer to select one SKU before enrichment, so values from neighboring rows are never merged. Broad manuals without clear product boundaries can therefore be accepted safely while leaving SKU-specific size, pressure, material, and end connection as `Missing` when the document does not tie them to one product.

## Demo path (three minutes)

1. On **Enrich Product**, choose **Load synthetic PDF**, then **Create evidence-backed record**. Choose **Try multi-SKU PDF** to demonstrate that two explicit product cards remain isolated and selectable.
2. Open **Inspect evidence**. Select **Pressure rating** to see its page-one snippet, deterministic validation, raw/canonical values, and review action.
3. To show a conflict, upload both generated files from `backend/demo_data/`: `synthetic_ball_valve_catalog.pdf` and `synthetic_conflicting_pressure.csv`. The same part number reports `600 WOG` versus `400 WOG` and must be reviewed. In the Workbench, choose **Run review agent** to show the stored, ranked human-action plan and its four-tool audit trace.
4. On **Catalog Health**, choose **Load synthetic batch** and process the 60-row batch. Filter the review queue and export it.

## Truth model

| Status | Meaning |
| --- | --- |
| Verified | Direct source evidence is retained and deterministic checks pass. |
| Inferred | A controlled title/category mapping yielded a plausible candidate, but it requires review. |
| Missing | No sufficient source evidence was found; the app does not fill a value. |
| Conflict | Sources disagree or a deterministic rule failed; all available evidence remains visible. |

The displayed confidence is a fixed, documented **review heuristic**, not an accuracy percentage or probability: direct evidence `0.95`, direct evidence after deterministic normalization `0.90`, inference `0.55`, missing `0.00`, and conflict/failing rule `0.25`.

## Test and build

```bash
cd /Users/nan/Documents/codes/unihack/backend
venv/bin/python -m pytest -q

cd /Users/nan/Documents/codes/unihack/frontend
npm run build
npm run lint
```

## Authorised real-world evaluation

The repository does not ship supplier data or an unmeasured “accuracy” number. It includes a local, reproducible evaluator that reads only an authorised, human-labelled ground-truth CSV and leaves its source files in place:

```bash
cd /Users/nan/Documents/codes/unihack/backend
venv/bin/python -m evaluation.run_evaluation /absolute/path/to/ground_truth.csv \
  --output /absolute/path/to/vericatalog-evaluation-output
```

See [backend/evaluation/README.md](backend/evaluation/README.md) for the required labels and responsible reporting boundary. Do not call any result “overall accuracy”; report the exact source set, inclusion rules, annotators, and field-level measures together.

## Repository layout

```text
backend/app/        FastAPI API, parsing, normalization, validation, storage
backend/tests/      Deterministic unit/service/demo-input tests
backend/evaluation/ Authorised-data evaluator and ground-truth template (no real data included)
backend/demo_data/  Generated, clearly marked synthetic fixtures
frontend/src/       React TypeScript three-screen interface
docs/               Product, architecture, demo, evaluation, and deck materials
submission/         Final PPTX, its local screenshot assets, and submission handoff notes
videos/             Validated silent demo-video source, project assets, and visual QA snapshots
```

## Data provenance

All included product sources are intentionally fabricated synthetic demo data. They are not supplier catalog data and must not be used for real-world accuracy, business-impact, or data-quality claims. See [docs/02-hackathon-compliance.md](docs/02-hackathon-compliance.md) and [backend/demo_data/README.md](backend/demo_data/README.md).

## Documentation

The Stage 1 plan and handoff material live in `docs/`, including requirements, compliance, scope, user flows, schema and validation, architecture, evaluation, demo script, pitch-deck outline, a ready-to-paste [submission description](docs/SUBMISSION_DESCRIPTION.md), implementation plan, data sources, and final submission checklist. The rendered editable deck and final owner steps are in [submission/README.md](submission/README.md).
