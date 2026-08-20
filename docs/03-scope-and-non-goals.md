# Scope and Non-Goals

## MVP Scope
The primary demo category is **Industrial valves and fittings**. This category was chosen because it has structured, judge-friendly attributes such as:
- Material
- Valve Type
- Size
- End Connection
- Pressure Rating
- Temperature Range
- Certifications

The system must handle:
1. **Inputs**: Synthetic PDFs, CSVs, XLSX, or partial manual entry.
2. **Extraction**: Mapping raw data to a standard PIM schema.
3. **Normalization**: Unit and value normalization (e.g., 25.4 mm -> 1 in).
4. **Validation**: Rule-based checks (required fields, type checks, unit compatibility, cross-source conflicts).
5. **Evidence**: Keeping track of exactly where each value came from.
6. **Outputs**: Exporting clean PIM-ready JSON and CSV.

## Non-Goals (Out of Scope)
- Generic Chatbot / RAG search app.
- Standalone synonym generation tool.
- Full E-commerce storefront or customer checkout flow.
- User authentication/Login/RBAC.
- Payment integration.
- Production Cloud Deployment.
- Vector database integration (keep it local/lightweight).
- Ambitious unfinished features (prefer a polished, complete 3-screen flow).

## Input and Processing Boundaries
- The MVP supports embedded-text and table-like PDFs, header-row CSV files, simple XLSX worksheets, and manual partial entry.
- Image-only/scanned PDF pages use locally installed Tesseract OCR when it is available. If it is unavailable or cannot read enough product context, the local demo returns a clear unsupported-input message instead of fabricating fields.
- A PDF may yield one strongest valve/fitting record in this prototype. The architecture keeps the record model extensible for multi-product parsing later.
- The system is local and single-user. SQLite persistence is for reproducibility, not a claim of production concurrency or deployment readiness.
