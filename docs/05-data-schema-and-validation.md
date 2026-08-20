# Data Schema and Validation

## Base PIM Schema
Every extracted attribute conforms to an auditable structure.

```json
{
  "field": "string (e.g., pressure_rating)",
  "raw_value": "string or number",
  "normalized_value": {
    "value": "string or number",
    "unit": "string (optional)"
  },
  "status": "enum (verified | inferred | missing | conflict)",
  "confidence": "number (0.0 to 1.0)",
  "evidence": [
    {
      "source_file": "string",
      "page": "number",
      "snippet": "string",
      "method": "string (e.g., pdf_text_extraction)"
    }
  ],
  "validation_results": [
    {
      "rule": "string",
      "status": "enum (pass | fail)"
    }
  ],
  "review_status": "enum (pending | approved | rejected | edited)"
}
```

## Key Attributes for Valves & Fittings
- `manufacturer`: String
- `mpn` (Manufacturer Part Number): String
- `product_title`: String
- `product_type`: String (e.g., "Ball Valve", "Gate Valve")
- `material`: String (e.g., "Stainless Steel 304", "Brass")
- `size`: Numeric + Unit (e.g., 1 inch)
- `end_connection`: String (e.g., "NPT", "Flanged")
- `pressure_rating`: Numeric + Unit (e.g., 600 WOG)
- `temperature_range`: Min/Max Numeric + Unit
- `certifications`: List of Strings
- `description`: String

## Validation Rules
1. **Required Fields**: MPN, Manufacturer, and Size must be present.
2. **Type Checking**: Size, Pressure, and Temperature must parse to numeric values.
3. **Unit Compatibility**: Convert known unit aliases to standard (e.g., `25.4 mm` -> `1 in`, `SS304` -> `Stainless Steel 304`).
4. **Plausibility (Valves)**: Pressure rating for standard brass ball valves typically doesn't exceed 1000 WOG. Flag anomalies.
5. **Cross-Source Conflict**: If PDF says "600 WOG" but CSV says "400 WOG", mark as `Conflict`.

## Evidence and Provenance Rules
- Every evidence item records `source_file`, `page` or `row`, a source `snippet`, and extraction `method`.
- `raw_value` remains immutable source context. A normalization adds a canonical value and a human-readable explanation; it does not overwrite raw evidence.
- A reviewer edit stores the decision, note, and reviewed value separately from the extracted value.
- A field can have several evidence objects. Conflicting evidence remains available after a reviewer approves or rejects the field.

## Normalization Policy
- `25.4 mm` normalizes to `1 in`, while retaining `25.4 mm` as the raw value.
- `SS304`, `SS 304`, and `AISI 304` normalize to `Stainless Steel 304`.
- `wog` and `W.O.G.` normalize to the canonical pressure unit `WOG` when a numeric rating is present.
- `-20 C to 180 C` normalizes to a structured Celsius range and a consistent display string.
- An unparseable value is preserved as raw text and routed to review; the application never silently guesses a conversion.

## Confidence Heuristic
Confidence is a transparent **review heuristic**, not a calibrated probability or a claim of extraction accuracy. The implementation uses fixed values: direct source evidence with passing rules is `0.95`; a directly evidenced value requiring deterministic unit/alias normalization is `0.90`; `Inferred` is `0.55`; `Missing` is `0.00`; and `Conflict` or a failing validation rule is `0.25`. Review actions do not change source confidence. The UI labels the value accordingly and shows it together with status, evidence, and validation results.

## Optional AI Candidate Mapping
An optional, server-side OpenAI-compatible chat-completions adapter can map unfamiliar source labels to the fixed schema. It is disabled unless a local `backend/.env` has `VERICATALOG_AI_ENABLED=true` plus a key, endpoint, and model. The adapter receives source text only; it must return a field, raw value, and verbatim `source_quote`. The application independently checks that both the raw value and quoted text occur in the supplied source before retaining the candidate as `optional_ai_candidate_mapping` evidence. AI-only candidates are always `Inferred` at `0.55`; the model never produces a Verified field, normalizes a value, resolves a conflict, or replaces raw evidence.

## Bounded Evidence Review Agent

The Review Agent is a deterministic, inspect-only orchestration layer that runs after enrichment. It reads the retained attribute status, review state, evidence count, and validation results, then returns a persisted plan containing:

- a task priority and one human action (`resolve_conflict`, `find_source_value`, or `verify_candidate`) for each exception;
- a human-readable reason and evidence-reference count; and
- a four-step audit trace: `identify_exceptions`, `inspect_provenance`, `evaluate_validation`, and `rank_human_actions`.

The plan is not a product mutation. It cannot update an attribute, alter review state, resolve a conflict, approve a field, export data, invoke a model, or access anything outside the retained product record. Its purpose is review triage and explainability, not extraction or accuracy scoring.
