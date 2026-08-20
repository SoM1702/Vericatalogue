# Competition-Readiness Plan

## Objective

Strengthen the existing evidence-first MVP where judges will probe hardest: a real catalog page with several SKUs, the difference between deterministic extraction and AI assistance, and measured rather than asserted quality.

This plan intentionally does not widen VeriCatalog Proof into a generic document-intelligence product. It remains a valves-and-fittings trust layer.

## 1. Multi-SKU PDF handling

### Problem

A supplier catalog page can describe several purchasable products. Treating the complete page as one record can mix material, pressure, and size across SKUs.

### MVP behaviour

1. Detect a catalog table only when its header maps to at least three supported product fields and includes a product identifier, title, or type.
2. Detect repeated labelled product cards only when separate part-number boundaries are present.
3. Return one review-selectable candidate record per detected row/card.
4. Add document-level manufacturer/family clues only when the selected row does not already provide that field; label those additions `Inferred`.
5. If row boundaries cannot be proven, retain the existing safe partial-document behaviour rather than mixing values.

### Acceptance checks

- Two explicitly labelled SKU cards become two separate records.
- A pipe- or column-delimited table with two product rows becomes two separate records.
- No candidate from one SKU appears in another SKU's evidence list.
- Existing single-product PDFs still return one record.

## 2. Evaluation harness

### Measurement boundary

The repository may include synthetic regression fixtures, but they are not an accuracy benchmark. A real-world accuracy claim needs authorised product-level documents and a locked ground-truth sheet.

### Harness inputs

An external CSV records `case_id`, local `source_path`, `record_index`, `field`, `expected_value`, and `expected_status`. The source files stay outside version control unless their licence permits redistribution.

### Reported measures

- document acceptance rate;
- selected-record coverage for multi-SKU documents;
- field-level exact-match precision and recall for direct (`Verified`) source facts;
- exact-match agreement for expected `Inferred` review candidates, reported separately from `Verified` facts;
- false-`Verified` count and rate;
- correct `Missing`/`Conflict` routing; and
- an auditable per-field result CSV.

The report must never collapse those measures into an unqualified marketing “accuracy” percentage.

## 3. Evidence-bound AI demonstration

The existing optional mapper is an extraction assistant, not an authority. It may help map unfamiliar source labels to the fixed schema only when both its value and quote are independently present in the source. Its output remains `Inferred`.

The UI must show whether AI mapping was active and how many grounded candidates it added. The deterministic path must still work if a key, model, or provider is unavailable.

## 4. Verification and handoff

- Add API journey coverage for upload → enrichment → review → export and batch processing.
- Run browser-level QA of the representative PDF, review-agent, and batch paths.
- Create a concise 16:9 English showcase video that uses the actual local UI and never claims unmeasured accuracy or savings.
- Initialize a nested Git repository in this project and prepare it for publication. Creating a remote and pushing it remains an owner action because it uses the owner's account credentials.

## Explicit non-goals

- No generic chatbot or free-form autonomous agent.
- No unattended approval, export, or source lookup by an AI model.
- No claim that arbitrary PDFs, drawings, or unrelated documents are fully extractable.
- No real supplier file is committed merely to improve a demo.
