# Hackathon Compliance

## Event Information
- **Event**: UniHack by Unilog / Hack2skill
- **Theme**: AI-Powered Product Intelligence for Industrial Commerce

## Constraints & Rules Adherence
1. **Data Provenance**: Use only properly licensed/public data or clearly marked synthetic demo data. Do not use confidential or unauthorized scraped datasets.
2. **Truthfulness**: Never fabricate accuracy, confidence, time-saved, or business-impact numbers. Metrics shown must be genuinely measured with explained methods.
3. **No Unilog Trademarks**: Do not claim integration with Unilog CX1 or use Unilog trademarks. This is a prototype designed for the same problem space, not a production Unilog product.
4. **Local Execution**: Do not deploy, publish externally, or require cloud account creation/credentials.
5. **No Hallucinations**: Inferred values must be presented as such. No silent filling of missing attributes.
6. **Optional AI Key Handling**: Any model key is loaded only by the local backend from an ignored `backend/.env`; it is never sent to the frontend, included in exports, or committed.

## Required Artifacts for Submission
- Functional MVP/POC (local web app)
- Idea/solution description
- Presentation deck (7 slides)
- Functional source-code repository link
- English documentation and presentation materials

## Dataset Provenance and Licensing Strategy
The repository will include only intentionally generated, clearly labelled synthetic valve and fitting documents and batch rows. Synthetic source filenames, in-file notices, and UI labels will make their status unambiguous. No confidential, proprietary, or scraped-without-permission supplier data will be added.

If public source data is introduced after the MVP, it must have a recorded source URL, licence, retrieval date, and permitted use in `docs/DATA_SOURCES.md` before it is processed or displayed. Demo metrics such as completeness and conflict count describe the processed synthetic batch only; they are not claims about real-world data quality or business impact.

## Event Link

The official event page to review immediately before submission is <https://hack2skill.com/event/unilog2026>. Event-platform requirements can change, so the owner should confirm the final deadline, required fields, and upload formats there before submitting.
