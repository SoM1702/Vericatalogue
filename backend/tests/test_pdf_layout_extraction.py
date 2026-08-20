from __future__ import annotations

import shutil

import pymupdf
import pytest

from app.extraction import SourceReadError, parse_pdf
from app.repository import ProductRepository
from app.service import CatalogService


def _text_pdf(lines: list[str]) -> bytes:
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    for index, line in enumerate(lines):
        page.insert_text((54, 62 + index * 34), line, fontsize=18)
    payload = document.tobytes()
    document.close()
    return payload


def _scanned_pdf(lines: list[str]) -> bytes:
    source = pymupdf.open(stream=_text_pdf(lines), filetype="pdf")
    pixmap = source[0].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    scanned = pymupdf.open()
    page = scanned.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=pixmap.tobytes("png"))
    payload = scanned.tobytes()
    scanned.close()
    source.close()
    return payload


def _candidate_map(rows):
    return {field: candidates[0] for field, candidates in rows[0].candidates.items()}


def test_table_like_pdf_creates_safe_partial_record_and_normalizes_global_units(tmp_path) -> None:
    payload = _text_pdf(
        [
            "Flowserve Flow Control GmbH",
            "ARGUS Ball Valve FK and HK",
            "Nominal Size",
            "DN 25",
            "End Connection",
            "Flanged",
            "Pressure Rating",
            "PN 16",
            "Temperature Range",
            "-20 C to 180 C",
            "Body Material",
            "316 Stainless Steel",
            "Certifications",
            "API 598",
        ]
    )

    rows = parse_pdf("manufacturer_table_layout.pdf", payload)
    candidates = _candidate_map(rows)
    assert candidates["manufacturer"].raw_value == "Flowserve Flow Control GmbH"
    assert candidates["manufacturer"].inferred is True
    assert candidates["product_title"].raw_value == "ARGUS Ball Valve FK and HK"
    assert candidates["product_type"].raw_value == "Ball Valve"
    assert candidates["size"].raw_value == "DN 25"
    assert candidates["pressure_rating"].raw_value == "PN 16"

    product = CatalogService(ProductRepository(tmp_path / "layout.sqlite3")).enrich(rows)
    attributes = {attribute.field: attribute for attribute in product.attributes}
    assert attributes["product_title"].status == "inferred"
    assert attributes["size"].normalized_value and attributes["size"].normalized_value.display == "1 in"
    assert attributes["pressure_rating"].normalized_value and attributes["pressure_rating"].normalized_value.display == "PN 16"
    assert attributes["material"].normalized_value and attributes["material"].normalized_value.display == "Stainless Steel 316"


def test_unrelated_pdf_still_returns_a_useful_error() -> None:
    payload = _text_pdf(["Quarterly planning notes", "Marketing budget and event schedule", "No product attributes are present."])
    with pytest.raises(SourceReadError, match="no identifiable valve/fitting attribute text"):
        parse_pdf("unrelated.pdf", payload)


def test_repeated_labelled_product_cards_are_kept_as_separate_skus() -> None:
    payload = _text_pdf(
        [
            "Manufacturer: Atlas Valve Inc.",
            "Manufacturer Part Number: AV-BV-100",
            "Product Title: 1 in Brass Ball Valve",
            "Product Type: Ball Valve",
            "Material: Brass",
            "Size: 1 in",
            "End Connection: NPT",
            "Pressure Rating: 600 WOG",
            "Manufacturer: Atlas Valve Inc.",
            "Manufacturer Part Number: AV-BV-200",
            "Product Title: 2 in Stainless Steel Ball Valve",
            "Product Type: Ball Valve",
            "Material: SS304",
            "Size: 2 in",
            "End Connection: Flanged",
            "Pressure Rating: 150 psi",
        ]
    )

    rows = parse_pdf("two_sku_cards.pdf", payload)
    assert len(rows) == 2
    assert rows[0].candidates["manufacturer_part_number"][0].raw_value == "AV-BV-100"
    assert rows[0].candidates["material"][0].raw_value == "Brass"
    assert rows[1].candidates["manufacturer_part_number"][0].raw_value == "AV-BV-200"
    assert rows[1].candidates["material"][0].raw_value == "SS304"
    assert all(candidate.evidence.method == "pdf_text_extraction" for candidate in rows[0].candidates["pressure_rating"])


def test_explicit_catalog_table_becomes_isolated_product_rows() -> None:
    payload = _text_pdf(
        [
            "Part Number | Type | Material | Pressure",
            "AT-100 | Ball Valve | Brass | 600 WOG",
            "AT-200 | Ball Valve | SS304 | 150 psi",
        ]
    )

    rows = parse_pdf("two_sku_table.pdf", payload)
    assert len(rows) == 2
    assert rows[0].candidates["manufacturer_part_number"][0].raw_value == "AT-100"
    assert rows[1].candidates["manufacturer_part_number"][0].raw_value == "AT-200"
    assert rows[1].candidates["material"][0].raw_value == "SS304"
    assert rows[0].candidates["pressure_rating"][0].evidence.method == "pdf_table_row_extraction"


def test_wrapped_pdf_spec_grid_recovers_family_level_values_without_inventing_skus(tmp_path) -> None:
    payload = _text_pdf(
        [
            "Bray Industrial, Inc.",
            "2 Piece Full Port Brass Ball Valves",
            "Size",
            "Pressure",
            "Rating",
            "Temperature",
            "Range",
            "End",
            "Connections",
            "Body",
            "Material",
            '1/4" to 2"',
            "600 psi WOG",
            "-50 F to +400 F",
            "Threaded - NPT",
            "Brass",
        ]
    )

    candidates = _candidate_map(parse_pdf("public_style_datasheet.pdf", payload))
    assert candidates["manufacturer"].raw_value == "Bray Industrial, Inc"
    assert candidates["product_title"].raw_value == "2 Piece Full Port Brass Ball Valves"
    assert candidates["product_type"].raw_value == "Ball Valve"
    assert candidates["material"].raw_value == "Brass"
    assert candidates["size"].raw_value == '1/4" to 2"'
    assert candidates["end_connection"].raw_value == "Threaded - NPT"
    assert candidates["pressure_rating"].raw_value == "600 psi WOG"
    assert candidates["temperature_range"].raw_value == "-50 F to +400 F"
    assert all(candidate.inferred for candidate in candidates.values())

    product = CatalogService(ProductRepository(tmp_path / "family.sqlite3")).enrich(parse_pdf("public_style_datasheet.pdf", payload))
    attributes = {attribute.field: attribute for attribute in product.attributes}
    assert attributes["size"].normalized_value and attributes["size"].normalized_value.display == '1/4" to 2"'
    assert attributes["pressure_rating"].normalized_value and attributes["pressure_rating"].normalized_value.display == "600 WOG"
    assert attributes["temperature_range"].normalized_value and attributes["temperature_range"].normalized_value.display == "-45.556 to 204.444 °C"


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Local Tesseract OCR is unavailable")
def test_scanned_labelled_pdf_uses_local_ocr() -> None:
    payload = _scanned_pdf(
        [
            "Manufacturer: Atlas Valve Inc.",
            "Product Title: 1 in Ball Valve",
            "Size: 1 in",
            "Pressure Rating: 600 WOG",
        ]
    )
    candidates = _candidate_map(parse_pdf("scanned_supplier.pdf", payload))
    assert candidates["manufacturer"].raw_value == "Atlas Valve Inc."
    assert any(
        candidate.evidence.method == "pdf_ocr_extraction"
        for field_candidates in candidates.values()
        for candidate in [field_candidates]
    )
