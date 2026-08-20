# Submission handoff

## Ready-to-upload materials

- `VeriCatalog-Proof-UniHack-2026.pptx` — seven-slide editable pitch deck, rendered and visually checked.
- `../docs/SUBMISSION_DESCRIPTION.md` — ready-to-paste solution description.
- `assets/` — local screenshots used in the deck. They show only synthetic demo data.
- `VeriCatalog-Proof-UniHack-2026-demo.mp4` — rendered 90-second, 1080p silent product demo, checked for duration and visual transition seams.
- `../videos/vericatalog-proof-demo/` — editable video source, project-owned screenshots, and visual QA snapshots. It intentionally contains no API key, real supplier data, or unmeasured accuracy claim.

## Before you submit

1. If you want optional AI mapping, copy `backend/.env.example` to `backend/.env`, add your OpenAI-compatible key, full `/chat/completions` endpoint, and model ID, then restart the backend. This is optional: deterministic proof mode already works without a key. Confirm `GET /api/ai/status` shows the intended model before your demo.
2. Publish the repository you own and copy its URL. The existing local Git repository has no published remote in this workspace.
3. Run the three-minute demo in the root `README.md` once after adding any key. Include the bounded Evidence Review Agent on the conflict record: it demonstrates a persisted four-tool audit trace and ranked human tasks without autonomous edits.
4. If the portal accepts a product video, upload `VeriCatalog-Proof-UniHack-2026-demo.mp4` after a team member has watched it once.
5. On the UniHack portal, paste `docs/SUBMISSION_DESCRIPTION.md`, upload the PPTX (and optional video) if requested, add the repository URL, and complete the final submission yourself.

The final portal fields, deadline, and required formats should be confirmed at <https://hack2skill.com/event/unilog2026> immediately before submission.
