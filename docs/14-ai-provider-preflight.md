# AI Provider Preflight

VeriCatalog Proof works without a model. Its deterministic extractor and evidence rules are the default, and the optional mapper only proposes unfamiliar label mappings. It cannot verify a value, approve a product, resolve a conflict, export data, or access a secret from the browser.

## Configure locally

```bash
cd /Users/nan/Documents/codes/unihack
cp backend/.env.example backend/.env
```

Set the ignored `backend/.env` file with the owner's OpenAI-compatible `/chat/completions` endpoint, model ID, and key. Keep `VERICATALOG_AI_BATCH_LIMIT=10` for the demo cost guardrail.

## Confirm the active state without exposing a key

Restart the backend and call:

```bash
curl http://127.0.0.1:8010/api/ai/status
```

Expected when configured:

```json
{"enabled": true, "configured": true, "model": "your-model-id", "mode": "grounded_candidate_mapping"}
```

Expected without a complete configuration:

```json
{"enabled": false, "configured": false, "model": null, "mode": "deterministic_only"}
```

The response intentionally never contains the API key or base URL. The UI shows the same active mode in its trust strip.

## Demo acceptance check

Use a document with an unfamiliar but source-supported field label. A candidate is acceptable only if its raw value and returned quote both appear in the source; it must remain `Inferred` and land in the human review queue. If the provider times out, is misconfigured, or returns ungrounded content, the deterministic result must remain usable and no automatic product mutation occurs.

For the Docker setup, use `docker compose --env-file backend/.env up --build` after this preflight. Never add `backend/.env` to Git, the slide deck, the team ZIP, or a demo recording.
