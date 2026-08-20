import io
import zipfile
from pathlib import Path

from app.demo_assets import BATCH_NAME, PDF_NAME, ensure_demo_assets
from app.extraction import parse_source
from app.repository import ProductRepository
from app.service import CatalogService


def test_synthetic_pdf_creates_complete_evidenced_record(tmp_path: Path) -> None:
    ensure_demo_assets()
    demo_pdf = Path(__file__).parents[1] / "demo_data" / PDF_NAME
    service = CatalogService(ProductRepository(tmp_path / "pdf.sqlite3"))
    product = service.enrich(parse_source(demo_pdf.name, demo_pdf.read_bytes()))
    pressure = next(attribute for attribute in product.attributes if attribute.field == "pressure_rating")
    size = next(attribute for attribute in product.attributes if attribute.field == "size")
    assert pressure.status == "verified"
    assert pressure.evidence[0].page == 1
    assert size.normalized_value and size.normalized_value.display == "1 in"


def test_synthetic_batch_has_sixty_products_and_health_metrics(tmp_path: Path) -> None:
    ensure_demo_assets()
    demo_csv = Path(__file__).parents[1] / "demo_data" / BATCH_NAME
    service = CatalogService(ProductRepository(tmp_path / "batch.sqlite3"))
    products = service.batch(parse_source(demo_csv.name, demo_csv.read_bytes()))
    metrics = service.health_metrics(products)
    assert len(products) == 60
    assert metrics["product_count"] == 60
    assert metrics["conflict_count"] >= 1
    assert metrics["missing_mandatory_fields"] >= 1


def test_simple_xlsx_preserves_header_columns() -> None:
    worksheet = """<?xml version='1.0' encoding='UTF-8'?>
    <worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'><sheetData>
      <row r='1'><c r='A1' t='inlineStr'><is><t>manufacturer</t></is></c><c r='B1' t='inlineStr'><is><t>manufacturer_part_number</t></is></c><c r='C1' t='inlineStr'><is><t>size</t></is></c></row>
      <row r='2'><c r='A2' t='inlineStr'><is><t>Northstar Flow Systems</t></is></c><c r='B2' t='inlineStr'><is><t>NFS-XLSX-1</t></is></c><c r='C2' t='inlineStr'><is><t>25.4 mm</t></is></c></row>
    </sheetData></worksheet>"""
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    rows = parse_source("synthetic_simple_input.xlsx", payload.getvalue())
    assert rows[0].candidates["manufacturer_part_number"][0].raw_value == "NFS-XLSX-1"
    assert rows[0].candidates["size"][0].raw_value == "25.4 mm"
