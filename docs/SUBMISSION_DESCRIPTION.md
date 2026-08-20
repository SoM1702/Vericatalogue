# VeriCatalog Proof — Submission Description

## One-line summary

VeriCatalog Proof is an evidence-first product-intelligence workflow for industrial valves and fittings that turns messy supplier documents into reviewable, PIM-ready product records.

## Problem

Industrial catalog attributes such as material, size, pressure rating, and temperature range cannot safely be treated as untraceable AI output. A missing or conflicting specification slows catalog onboarding and requires a data steward to rediscover the original source before they can make a decision.

## Solution

VeriCatalog Proof accepts text PDFs, CSV files, simple XLSX workbooks, or a partial manual entry. It extracts a fixed product schema, preserves raw values and source snippets, applies deterministic normalization and validation, and labels every field as Verified, Inferred, Missing, or Conflict. The Evidence & Review Workbench lets a reviewer approve, reject, or correct a field without deleting its original evidence. JSON/CSV product exports and a review-queue CSV make the result PIM-ready.

## What makes it different

- Field-level lineage: every retained value keeps its source file, location/snippet, and extraction method.
- Multi-SKU safety: clearly bounded PDF product cards and catalog-table rows remain separate; the reviewer explicitly selects the SKU rather than receiving a merged record.
- Deterministic trust layer: normalizers and rules explain canonical units and flag missing, implausible, duplicate, or conflicting values.
- Human review by design: AI-only candidates stay Inferred; conflicts retain every competing source value.
- Bounded Review Agent: four local inspect-only tools turn exceptions, provenance, and validation results into a ranked human queue with a persisted audit trace. It cannot edit, approve, resolve, export, or create product facts.
- Optional, grounded AI mapping: a user-supplied OpenAI-compatible model can map unfamiliar source labels only when the app independently finds both the model's raw value and quoted evidence in the source text. No AI key is sent to the browser.
- Reproducible demo: the shipped PDF, CSV, and 60-row batch are explicitly labelled synthetic, so no unauthorised supplier data is used.

## Demo flow

1. Process the supplied synthetic ball-valve PDF to create an evidence-backed record. Optionally load the synthetic multi-SKU PDF to show the record selector and no-cross-SKU merge safeguard.
2. Inspect a field to see its raw text, normalized value, validation result, and page-level evidence.
3. Add the supplied conflicting CSV to surface `600 WOG` versus `400 WOG` as a review-required conflict, then run the Evidence Review Agent to expose its local audit trail and ranked human tasks.
4. Process the 60-row synthetic batch to view completeness, missing required fields, conflicts, duplicate candidates, and priority review rows.

## Tech

React + TypeScript (Vite) frontend; FastAPI + Pydantic backend; PyMuPDF PDF extraction; deterministic Python normalization; SQLite local persistence; optional OpenAI-compatible, server-side candidate-mapping adapter.

## Responsible-use statement

All bundled inputs are synthetic. The demo reports only properties calculated from the processed synthetic batch and does not claim real-world extraction accuracy, time savings, ROI, or integration with Unilog products.
