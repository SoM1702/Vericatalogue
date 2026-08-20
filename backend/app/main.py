from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from .config import CORS_ORIGINS, DB_PATH, DEMO_DIR, ensure_runtime_directories
from .ai_mapping import AIMapperError, ai_status, enrich_with_ai_candidates
from .demo_assets import BATCH_NAME, CONFLICT_NAME, MULTI_SKU_PDF_NAME, PDF_NAME, ensure_demo_assets
from .extraction import SourceReadError, manual_source, parse_source
from .models import BatchResponse, EnrichmentResponse, ProductRecord, RecordOption, ReviewAgentPlan, ReviewRequest
from .repository import ProductRepository
from .service import CatalogService


ensure_runtime_directories()
ensure_demo_assets()
service = CatalogService(ProductRepository(DB_PATH))

app = FastAPI(
    title="VeriCatalog Proof API",
    version="0.1.0",
    description="Evidence-first local product intelligence for industrial valves and fittings.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ORIGINS if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)


async def _read_sources(files: list[UploadFile]) -> list:
    sources = []
    for file in files:
        if not file.filename:
            continue
        payload = await file.read()
        try:
            sources.extend(parse_source(file.filename, payload))
        except SourceReadError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return sources


def _record_options(source_rows: list) -> list[RecordOption]:
    """Describe parser-proven SKU rows without making an ungrounded product claim."""
    options: list[RecordOption] = []
    for index, source in enumerate(source_rows):
        mpn = next(iter(source.candidates.get("manufacturer_part_number", [])), None)
        title = next(iter(source.candidates.get("product_title", [])), None)
        product_type = next(iter(source.candidates.get("product_type", [])), None)
        label = mpn.raw_value if mpn else title.raw_value if title else product_type.raw_value if product_type else f"Detected record {index + 1}"
        evidence = mpn.evidence if mpn else title.evidence if title else product_type.evidence if product_type else None
        options.append(
            RecordOption(
                index=index,
                label=label,
                source_file=source.source_file,
                page=evidence.page if evidence else None,
                detected_fields=sorted(source.candidates),
            )
        )
    return options


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "VeriCatalog Proof API", "mode": "local deterministic"}


@app.get("/api/ai/status")
def get_ai_status() -> dict:
    """Expose configuration state only; keys and provider URLs never leave the server."""
    return ai_status()


@app.get("/api/demo-files/{filename}")
def demo_file(filename: str) -> FileResponse:
    if filename not in {PDF_NAME, MULTI_SKU_PDF_NAME, CONFLICT_NAME, BATCH_NAME}:
        raise HTTPException(status_code=404, detail="Demo file not found.")
    path = DEMO_DIR / filename
    if not path.exists():
        ensure_demo_assets()
    media_type = "application/pdf" if path.suffix == ".pdf" else "text/csv"
    return FileResponse(path, media_type=media_type, filename=filename)


@app.post("/api/enrich", response_model=EnrichmentResponse)
async def enrich_product(
    files: list[UploadFile] = File(default=[]),
    manual_title: str | None = Form(default=None),
    manual_mpn: str | None = Form(default=None),
    record_index: int = Form(default=0),
) -> EnrichmentResponse:
    sources = await _read_sources(files)
    record_options: list[RecordOption] = []
    if len(files) == 1 and files[0].filename and files[0].filename.lower().endswith(".pdf") and len(sources) > 1:
        record_options = _record_options(sources)
        if record_index < 0 or record_index >= len(sources):
            raise HTTPException(status_code=422, detail=f"Choose one of the {len(sources)} detected product records.")
        sources = [sources[record_index]]
    manual = manual_source(manual_title, manual_mpn)
    if manual:
        sources.append(manual)
    if not sources:
        raise HTTPException(status_code=422, detail="Upload a PDF, CSV, XLSX, or provide a partial title or manufacturer part number.")
    ai_warning = None
    try:
        ai_candidate_count = await enrich_with_ai_candidates(sources)
    except AIMapperError as exc:
        # AI is an optional convenience layer. A provider outage must never block
        # the deterministic evidence-first workflow or discard a user's upload.
        ai_candidate_count = 0
        ai_warning = str(exc)
    product = service.enrich(sources)
    message = "Product record created with retained source evidence."
    if record_options:
        message += f" Selected catalog record {record_index + 1} of {len(record_options)}; other SKU values were not merged."
    if ai_candidate_count:
        message += f" Added {ai_candidate_count} grounded AI candidate field(s) for review."
    if ai_warning:
        message += " Optional AI mapping was unavailable; deterministic extraction completed."
    return EnrichmentResponse(
        product=product,
        message=message,
        record_options=record_options,
        ai_candidate_count=ai_candidate_count,
    )


@app.post("/api/batch", response_model=BatchResponse)
async def process_batch(file: UploadFile = File(...)) -> BatchResponse:
    if not file.filename:
        raise HTTPException(status_code=422, detail="Choose a CSV or XLSX batch file.")
    sources = await _read_sources([file])
    ai_warning = None
    try:
        await enrich_with_ai_candidates(sources, batch=True)
    except AIMapperError as exc:
        ai_warning = str(exc)
    products = service.batch(sources)
    message = f"Processed {len(products)} product rows locally."
    if ai_warning:
        message += " Optional AI mapping was unavailable; deterministic processing completed."
    return BatchResponse(
        products=products,
        metrics=service.health_metrics(products),
        message=message,
    )


@app.get("/api/products/{product_id}", response_model=ProductRecord)
def get_product(product_id: str) -> ProductRecord:
    product = service.repository.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product record not found.")
    return product


@app.get("/api/products/{product_id}/review-agent/latest", response_model=ReviewAgentPlan)
def get_latest_review_agent_plan(product_id: str) -> ReviewAgentPlan:
    product = service.repository.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product record not found.")
    plan = service.repository.latest_review_agent_run(product_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No Evidence Review Agent run is available for this product yet.")
    return plan


@app.post("/api/products/{product_id}/review-agent/plan", response_model=ReviewAgentPlan)
def run_review_agent(product_id: str) -> ReviewAgentPlan:
    plan = service.run_review_agent(product_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Product record not found.")
    return plan


@app.patch("/api/products/{product_id}/attributes/{field}", response_model=ProductRecord)
def review_attribute(product_id: str, field: str, request: ReviewRequest) -> ProductRecord:
    try:
        product = service.review(product_id, field, request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not product:
        raise HTTPException(status_code=404, detail="Product record or attribute not found.")
    return product


@app.get("/api/products/{product_id}/export")
def export_product(product_id: str, format: str = "json") -> Response:
    product = service.repository.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product record not found.")
    safe_id = product.id.replace("/", "_")
    if format == "json":
        return Response(
            content=product.model_dump_json(indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{safe_id}.json"'},
        )
    if format == "csv":
        return Response(
            content=service.product_csv(product),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{safe_id}.csv"'},
        )
    raise HTTPException(status_code=422, detail="Export format must be json or csv.")


@app.get("/api/review-queue/export")
def export_review_queue() -> Response:
    content = service.review_queue_csv(service.repository.list_all())
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="vericatalog-review-queue.csv"'},
    )
