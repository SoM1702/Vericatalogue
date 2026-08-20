# Authorised Evaluation Harness

This directory contains a **local-only measurement harness**, not a bundled real-world dataset. It never copies source files into the app upload folder or this repository.

## Prepare a benchmark

1. Obtain permission to use each supplier document for evaluation.
2. Store those documents outside this repository, for example in a private `authorised_sources/` directory.
3. Copy `ground_truth_template.csv` beside the documents and add one locked expected field per row.
4. Use zero-based `record_index` to select a SKU where a PDF has multiple detected catalog records.
5. Have a second team member check the ground truth before running the evaluator.

`expected_status` must be one of `verified`, `inferred`, `missing`, or `conflict`. A source-backed field should have a canonical human-checked `expected_value`; a `missing` field has an empty value.

## Run it

```bash
cd /Users/nan/Documents/codes/unihack/backend
venv/bin/python -m evaluation.run_evaluation /absolute/path/to/ground_truth.csv \
  --output /absolute/path/to/vericatalog-evaluation-output
```

The output directory contains:

- `summary.json` — document acceptance, selected-record coverage, exact-match precision/recall for `Verified` fields, inferred-candidate exact-match rate, false-`Verified` count/rate, and missing/conflict routing;
- `field_results.csv` — one auditable comparison per expected field; and
- `report.md` — a compact human-readable summary.

An inferred-candidate exact match means a review-required candidate agrees with a locked label; it is not a `Verified` extraction rate. Do not call any resulting number “overall accuracy.” Report the source set, its licence/permission, inclusion rules, document types, annotator process, and the individual measures together.
