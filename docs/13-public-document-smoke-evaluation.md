# Public Document Smoke Evaluation

## Purpose and boundary

This is a parser smoke evaluation on one publicly available manufacturer data sheet. It demonstrates that the PDF layout path can extract a product-family record without fabricating individual SKUs. It is **not** an overall accuracy study, an independently labelled benchmark, a supplier-data release, or evidence of business impact.

The source PDF was downloaded only into an excluded temporary directory on 20 August 2026 and was not committed, packaged, or redistributed. Before evaluating any non-public material, obtain the supplier's authorisation and keep the source outside version control.

## Source and scope

| Item | Value |
| --- | --- |
| Source | [Bray Flow-Tek Series 51 data sheet](https://www.bray.com/docs/default-source/brochures/product-brochures/threaded-ball-valves-s51-pb-en-us.pdf?sfvrsn=f4de1137_18) |
| Document scope | One two-page official product-family data sheet |
| Candidate record | One family-level record; no individual SKU is invented |
| Checked fields | Eight: title, type, manufacturer, size range, pressure, temperature, end connection, material |
| Labels | Preliminary project-prepared labels; second-reviewer sign-off is still required |

## Result

The evaluator accepted the document and matched **8 of 8 expected review candidates** exactly. All eight values were intentionally expected and returned as `Inferred`, because their evidence came from a compact, wrapped specification grid describing a family rather than a labelled, purchasable individual SKU. The run therefore has no applicable `Verified` precision or recall metric and reports no general “accuracy” percentage.

| Measure | Result | Interpretation |
| --- | ---: | --- |
| Document acceptance | 1 / 1 | This one embedded-text PDF was accepted |
| Selected-record coverage | 1 / 1 | The single family record was selected |
| Inferred-candidate exact match | 8 / 8 | Preliminary labels agree with evidence-bound review candidates |
| Verified precision / recall | N/A | No direct, SKU-level `Verified` labels were included |
| False `Verified` values | 0 | The parser did not overstate compact-grid values as verified |

## Reproduction

Keep the downloaded PDF and a reviewed `ground_truth.csv` outside the repository, then run:

```bash
cd /Users/nan/Documents/codes/unihack/backend
venv/bin/python -m evaluation.run_evaluation /absolute/path/to/ground_truth.csv \
  --output /absolute/path/to/vericatalog-evaluation-output
```

The generated `summary.json`, `field_results.csv`, and `report.md` record the source paths and per-field results without copying the source PDF into the project.

## What must happen before any accuracy claim

1. A second team member independently reviews and locks the labels for this smoke case.
2. Expand to at least 20 authorised, product-level documents covering text PDFs, tables, scanned pages, and known difficult layouts.
3. Publish the inclusion rules, annotation method, field-level `Verified` precision/recall, `Inferred` candidate agreement, and failure routing together.
4. Report no aggregate claim when the source mix, labels, or reviewers are incomplete.
