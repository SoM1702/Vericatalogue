# User Flows

## Flow 1: Enrich Product (Single Item)
1. User navigates to the "Enrich Product" screen.
2. User uploads a supplier PDF, CSV, XLSX, or enters a partial part number.
3. User selects the category: "Industrial Valves & Fittings".
4. The system processes the file, extracting and normalizing attributes.
5. The UI displays the generated product record in a clean, structured form showing key fields (manufacturer, MPN, title, type, material, size, pressure rating, etc.).

## Flow 2: Evidence & Review Workbench
1. From the generated product record, the user clicks to inspect a specific attribute.
2. The UI expands to show the Evidence Workbench for that attribute:
   - Raw extracted value vs Normalized value.
   - Status tag: `Verified`, `Inferred`, `Missing`, or `Conflict`.
   - Validation result (e.g., "Passed type check").
   - Source snippet (filename, page number, and the exact text/table it came from).
3. For fields marked `Inferred` or `Conflict`, the user selects "Approve", "Reject", or manually edits the value.
4. Once all conflicts are resolved, the user clicks "Export" to download a PIM-ready JSON or CSV.

## Flow 3: Catalog Health (Batch Processing)
1. User navigates to the "Catalog Health" dashboard.
2. User uploads a batch CSV containing multiple products.
3. The system processes the batch and displays aggregate metrics:
   - Total products processed.
   - Completeness score (%).
   - Total conflicts or fields requiring review.
4. A table lists the highest-priority products needing review.
5. User can filter the list by status (e.g., "Show only conflicts") and export the review queue.

## Error and Empty States
- Unsupported extensions, blank files, missing headers, unreadable PDFs, and sources with no extractable product return a plain-language message and a next step.
- Low-text scanned PDF pages attempt local Tesseract OCR when installed. A table-like or document-level cue becomes `Inferred` with source evidence; uncertain SKU-specific fields remain `Missing` rather than becoming unsupported facts.
- No selected product produces a guided empty state; placeholder product values are never shown as data.
- Statuses use text labels and icons in addition to colour so review state does not rely on colour alone.
