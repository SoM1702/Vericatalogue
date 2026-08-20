from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit

import pymupdf

from app import main
from app.demo_assets import MULTI_SKU_PDF_NAME, PDF_NAME, ensure_demo_assets
from app.extraction import parse_pdf
from app.repository import ProductRepository
from app.service import CatalogService


def _pdf(lines: list[str]) -> bytes:
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    for index, line in enumerate(lines):
        page.insert_text((54, 62 + index * 26), line, fontsize=13)
    payload = document.tobytes()
    document.close()
    return payload


def _configure_service(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(main, "service", CatalogService(ProductRepository(tmp_path / "api.sqlite3")))


def _request(method: str, url: str, body: bytes = b"", headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    parsed = urlsplit(url)
    sent: list[dict] = []
    request_sent = False

    async def receive() -> dict:
        nonlocal request_sent
        if request_sent:
            return {"type": "http.disconnect"}
        request_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode(),
        "query_string": parsed.query.encode(),
        "root_path": "",
        "headers": [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    asyncio.run(main.app(scope, receive, send))
    response_start = next(message for message in sent if message["type"] == "http.response.start")
    response_body = b"".join(message.get("body", b"") for message in sent if message["type"] == "http.response.body")
    return response_start["status"], response_body


def _multipart(fields: dict[str, str], filename: str, payload: bytes, content_type: str) -> tuple[bytes, str]:
    boundary = "----vericatalog-test-boundary"
    body = bytearray()
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'.encode())
    body.extend(f"Content-Type: {content_type}\r\n\r\n".encode())
    body.extend(payload)
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def test_api_enrichment_selects_one_multi_sku_record_and_exports_it(tmp_path: Path, monkeypatch) -> None:
    _configure_service(tmp_path, monkeypatch)
    payload = _pdf(
        [
            "Manufacturer Part Number: API-100",
            "Product Title: 1 in Brass Ball Valve",
            "Product Type: Ball Valve",
            "Material: Brass",
            "Size: 1 in",
            "Pressure Rating: 600 WOG",
            "Manufacturer Part Number: API-200",
            "Product Title: 2 in SS304 Ball Valve",
            "Product Type: Ball Valve",
            "Material: SS304",
            "Size: 2 in",
            "Pressure Rating: 150 psi",
        ]
    )

    request_body, content_type = _multipart({"record_index": "1"}, "catalog_cards.pdf", payload, "application/pdf")
    status, response_body = _request("POST", "/api/enrich", request_body, {"content-type": content_type, "content-length": str(len(request_body))})
    assert status == 200
    body = json.loads(response_body)
    assert len(body["record_options"]) == 2
    assert body["ai_candidate_count"] == 0
    assert "Selected catalog record 2 of 2" in body["message"]
    attributes = {attribute["field"]: attribute for attribute in body["product"]["attributes"]}
    assert attributes["manufacturer_part_number"]["raw_value"] == "API-200"
    assert attributes["material"]["raw_value"] == "SS304"

    product_id = body["product"]["id"]
    review_payload = json.dumps({"action": "approve", "note": "Checked selected SKU card."}).encode()
    status, _ = _request("PATCH", f"/api/products/{product_id}/attributes/material", review_payload, {"content-type": "application/json"})
    assert status == 200
    status, exported = _request("GET", f"/api/products/{product_id}/export?format=json")
    assert status == 200
    assert b"API-200" in exported

    request_body, content_type = _multipart({"record_index": "-1"}, "catalog_cards.pdf", payload, "application/pdf")
    status, response_body = _request("POST", "/api/enrich", request_body, {"content-type": content_type, "content-length": str(len(request_body))})
    assert status == 422
    assert "Choose one of the 2 detected product records" in json.loads(response_body)["detail"]


def test_api_demo_upload_and_batch_journey(tmp_path: Path, monkeypatch) -> None:
    _configure_service(tmp_path, monkeypatch)
    ensure_demo_assets()
    demo_directory = Path(__file__).parents[1] / "demo_data"
    request_body, content_type = _multipart({}, PDF_NAME, (demo_directory / PDF_NAME).read_bytes(), "application/pdf")
    status, response_body = _request("POST", "/api/enrich", request_body, {"content-type": content_type, "content-length": str(len(request_body))})
    assert status == 200
    product_id = json.loads(response_body)["product"]["id"]
    status, _ = _request("GET", f"/api/products/{product_id}/export?format=csv")
    assert status == 200

    batch_payload = (
        "manufacturer,manufacturer_part_number,product_title,product_type,material,size,end_connection,pressure_rating\n"
        "Atlas,API-BATCH-1,1 in Ball Valve,Ball Valve,Brass,1 in,NPT,600 WOG\n"
    ).encode()
    request_body, content_type = _multipart({}, "api_batch.csv", batch_payload, "text/csv")
    # The batch endpoint names its multipart file field differently from enrichment.
    request_body = request_body.replace(b'name="files"', b'name="file"', 1)
    status, response_body = _request("POST", "/api/batch", request_body, {"content-type": content_type, "content-length": str(len(request_body))})
    assert status == 200
    assert json.loads(response_body)["metrics"]["product_count"] == 1


def test_generated_multi_sku_demo_is_parseable_as_two_isolated_records() -> None:
    ensure_demo_assets()
    demo_directory = Path(__file__).parents[1] / "demo_data"
    records = parse_pdf(MULTI_SKU_PDF_NAME, (demo_directory / MULTI_SKU_PDF_NAME).read_bytes())
    assert [record.candidates["manufacturer_part_number"][0].raw_value for record in records] == ["NFS-BV-2001", "NFS-BV-2002"]
    assert [record.candidates["manufacturer"][0].raw_value for record in records] == ["Northstar Flow Systems", "Northstar Flow Systems"]
    assert records[0].candidates["pressure_rating"][0].raw_value == "600 WOG"
    assert records[1].candidates["pressure_rating"][0].raw_value == "300 WOG"
