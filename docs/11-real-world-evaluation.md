# Real-World Document Evaluation — 2026-08-20

## Purpose and boundary

This is a diagnostic check of the current MVP against one public, non-synthetic manufacturer PDF. It is **not** a field-level accuracy benchmark and must not be used as an overall accuracy claim.

The evaluation file was downloaded only to a temporary local folder and is not included in the repository, demo data, exports, or team-share archive.

## Public source evaluated

| Item | Value |
| --- | --- |
| Publisher | Flowserve |
| Document | *ARGUS Ball Valve FK and HK — Instructions* (`VAIOM001024_EN_A4`) |
| Official URL | `https://www.flowserve.com/sites/default/files/dam/documents/VAIOM001024_EN_A4.pdf?t.download=true` |
| Retrieval date | 2026-08-20 |
| Source type | Public manufacturer technical-instructions PDF; it is not a labelled single-SKU catalog record |
| Repository treatment | Not committed or redistributed |

## Method

1. Download the exact public PDF to an operating-system temporary folder.
2. Run the updated PDF parser directly, without editing, relabelling, converting, or supplementing the document.
3. Record document readability and parser acceptance before any field-level comparison.

## Observed result

| Measure | Result |
| --- | --- |
| PDF pages opened by PyMuPDF | 52 |
| Text characters extracted by PyMuPDF | 79,511 |
| Documents accepted by the updated structured parser | 1 / 1 |
| Structured attributes returned | 3: manufacturer, product title, product type |
| Returned status | All three `Inferred`, with page-level `pdf_layout_inference` evidence |
| Field precision / recall / exact-match accuracy | Not measurable: the source is a product-family technical manual, not a labelled single-SKU ground-truth record |

The prior parser returned `contains no readable labelled text`. This was not an OCR failure: PyMuPDF extracted substantial text. The updated parser identifies the recurring document title `ARGUS Ball Valve FK and HK`, product type `Ball Valve`, and manufacturer `Flowserve Flow Control GmbH` from document layout/context. It deliberately leaves SKU-specific size, pressure, material, and end connection as `Missing`: this manual covers a family and does not safely bind those values to one purchasable record.

## Interpretation

This is a **1/1 document-acceptance result for this one real-world source**, not a field-level extraction-accuracy score. The result demonstrates that the PDF path can safely accept a non-synthetic manufacturer manual and route it to review without inventing a SKU. It does not demonstrate broad supplier-catalog accuracy.

The previously shown `93.3%` remains a synthetic-batch completeness metric only. It must not be presented as real-world accuracy.

## What is needed for a valid accuracy number

Before reporting accuracy, create an authorised and reproducible evaluation set of at least 25 product-level documents with a locked field-level ground-truth sheet. Report, separately:

- document acceptance / extraction coverage;
- normalized exact-match precision and recall by field;
- false-verification rate (especially pressure, material, size, and end connection);
- missing/conflict-routing accuracy; and
- source, licence/terms, retrieval date, annotator rules, and known exclusions.

Do not add real supplier files to the repository unless their reuse terms are recorded and allow it.
