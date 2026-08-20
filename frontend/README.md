# VeriCatalog Proof frontend

This React 19 + TypeScript + Vite + Tailwind 4 application is the interface for the local VeriCatalog Proof API. It retains the original starter stack and now implements the three MVP screens:

- Enrich Product
- Evidence & Review Workbench
- Catalog Health

Run the FastAPI backend first (default `http://localhost:8000`), then:

```bash
npm install
npm run dev
```

For a non-default local backend address, add `frontend/.env.local`:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8010
```

Quality checks:

```bash
npm run build
npm run lint
```

See the project-level [README](../README.md) for setup, data provenance, documentation, and the demo path.
