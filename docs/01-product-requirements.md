# VeriCatalog Proof: Product Requirements

## Problem Statement
AI can easily extract catalog data, but industrial commerce cannot trust it without proof. Product catalogs, specifically for items like industrial valves and fittings, contain critical structured attributes (material, pressure rating, etc.). Traditional AI extraction provides answers but no lineage. VeriCatalog Proof serves as a "trust layer" that makes every product attribute auditable and verifiable before it ever reaches a Product Information Management (PIM) system.

## Target Audience
- Data Stewards and Catalog Managers at industrial distributors.
- PIM Administrators who need to ingest supplier data quickly without compromising accuracy.

## Hackathon Judging Alignment
This product directly addresses "AI-Powered Product Intelligence for Industrial Commerce" for UniHack by Unilog. It emphasizes:
- Structured data generation from unstructured supplier sources (PDFs, CSVs).
- Accuracy and consistency through field-level evidence and validation.
- Explainable, traceable outputs rather than "black-box" AI generation.
- Human-in-the-loop validation of conflicts and anomalies.

## Core Features
1. **Enrich Product**: Single-item extraction from PDF/CSV with schema mapping and unit normalization.
2. **Evidence & Review Workbench**: A side-by-side view showing extracted values next to the exact source snippet (page, text). Enables users to Approve, Reject, or Edit inferred/conflicting fields.
3. **Catalog Health**: Batch processing overview showing completeness scores, conflict counts, and review priorities.

## Expected Outcomes
- Make source-backed catalog attributes inspectable before PIM export.
- Prevent recognized unit mismatches (e.g., metric and imperial size notation) from being silently normalized without explanation.
- Identify and flag deterministic supplier-data conflicts for review.

## Required Truth Behaviors
- A value cannot be marked `Verified` without direct retained source evidence.
- An inferred value must remain visibly `Inferred` and requires human review.
- Missing evidence results in `Missing`, not a filled value.
- Conflicting sources retain both values and evidence; a review action never erases provenance.
- Product health metrics are calculated from processed records by documented formulas. The MVP does not claim an unmeasured accuracy rate, time saving, or business outcome.
