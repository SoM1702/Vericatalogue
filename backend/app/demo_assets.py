from __future__ import annotations

import csv
from pathlib import Path

import pymupdf

from .config import DEMO_DIR


PDF_NAME = "synthetic_ball_valve_catalog.pdf"
MULTI_SKU_PDF_NAME = "synthetic_multi_sku_catalog.pdf"
CONFLICT_NAME = "synthetic_conflicting_pressure.csv"
BATCH_NAME = "synthetic_valve_batch.csv"


def ensure_demo_assets() -> None:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    _create_pdf(DEMO_DIR / PDF_NAME)
    _create_multi_sku_pdf(DEMO_DIR / MULTI_SKU_PDF_NAME)
    _create_conflict_csv(DEMO_DIR / CONFLICT_NAME)
    _create_batch_csv(DEMO_DIR / BATCH_NAME)
    notice = DEMO_DIR / "README.md"
    if not notice.exists():
        notice.write_text(
            "# Synthetic demo data\n\nAll files in this directory are intentionally fabricated for the VeriCatalog Proof demo. They are not supplier catalog data and must not be used to make real-world accuracy or business-impact claims.\n",
            encoding="utf-8",
        )


def _create_pdf(path: Path) -> None:
    # This is an application-owned synthetic fixture. Recreate it so source text stays
    # synchronized with the demo workflow after a local code update.
    if path.exists():
        path.unlink()
    document = pymupdf.open()
    page = document.new_page(width=612, height=792)
    lines = [
        "SYNTHETIC DEMO DATA — NOT A REAL SUPPLIER CATALOG",
        "Manufacturer: Northstar Flow Systems",
        "Manufacturer Part Number: NFS-BV-1001",
        "Product Title: 1 in Full Port Ball Valve",
        "Product Type: Ball Valve",
        "Material: SS304",
        "Size: 25.4 mm",
        "End Connection: NPT",
        "Pressure Rating: 600 WOG",
        "Temperature Range: -20 C to 180 C",
        "Certifications: API 607; ISO 9001",
        "Description: Synthetic full-port isolation valve for demo review.",
    ]
    page.insert_text((56, 58), "\n".join(lines), fontsize=11, fontname="helv", lineheight=1.45)
    document.set_metadata({"title": "Synthetic VeriCatalog Proof valve catalog", "author": "VeriCatalog Proof demo"})
    document.save(path)
    document.close()


def _create_multi_sku_pdf(path: Path) -> None:
    """Create two explicitly-labelled, intentionally separate demo product cards."""
    if path.exists():
        path.unlink()
    document = pymupdf.open()
    page = document.new_page(width=612, height=792)
    lines = [
        "SYNTHETIC DEMO DATA — NOT A REAL SUPPLIER CATALOG",
        "MULTI-SKU CATALOG EXAMPLE — EACH CARD IS A SEPARATE PRODUCT",
        "",
        "Manufacturer: Northstar Flow Systems",
        "Manufacturer Part Number: NFS-BV-2001",
        "Product Title: 1 in Full Port Ball Valve",
        "Product Type: Ball Valve",
        "Material: SS304",
        "Size: 1 in",
        "End Connection: NPT",
        "Pressure Rating: 600 WOG",
        "",
        "Manufacturer: Northstar Flow Systems",
        "Manufacturer Part Number: NFS-BV-2002",
        "Product Title: 2 in Full Port Ball Valve",
        "Product Type: Ball Valve",
        "Material: Brass",
        "Size: 2 in",
        "End Connection: Flanged",
        "Pressure Rating: 300 WOG",
    ]
    page.insert_text((56, 48), "\n".join(lines), fontsize=10.5, fontname="helv", lineheight=1.26)
    document.set_metadata({"title": "Synthetic multi-SKU VeriCatalog Proof catalog", "author": "VeriCatalog Proof demo"})
    document.save(path)
    document.close()


def _create_conflict_csv(path: Path) -> None:
    if path.exists():
        return
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "manufacturer",
                "manufacturer_part_number",
                "product_title",
                "product_type",
                "material",
                "size",
                "end_connection",
                "pressure_rating",
                "temperature_range",
                "certifications",
                "description",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "manufacturer": "Northstar Flow Systems",
                "manufacturer_part_number": "NFS-BV-1001",
                "product_title": "1 in Full Port Ball Valve",
                "product_type": "Ball Valve",
                "material": "Stainless Steel 304",
                "size": "1 in",
                "end_connection": "NPT",
                "pressure_rating": "400 WOG",
                "temperature_range": "-20 C to 180 C",
                "certifications": "API 607; ISO 9001",
                "description": "Synthetic conflicting supplier row for demo review.",
            }
        )


def _create_batch_csv(path: Path) -> None:
    if path.exists():
        return
    headers = [
        "manufacturer",
        "manufacturer_part_number",
        "product_title",
        "product_type",
        "material",
        "size",
        "end_connection",
        "pressure_rating",
        "temperature_range",
        "certifications",
        "description",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        for number in range(1, 61):
            mpn = "NFS-BV-1001" if number == 60 else f"NFS-BV-{1000 + number:04d}"
            material = "SS304" if number % 3 else "Brass"
            size = "25.4 mm" if number % 2 else "1 in"
            row = {
                "manufacturer": "Northstar Flow Systems",
                "manufacturer_part_number": mpn,
                "product_title": f"{size} Full Port Ball Valve",
                "product_type": "Ball Valve" if number % 5 else "",
                "material": "" if number % 13 == 0 else material,
                "size": size,
                "end_connection": "" if number % 11 == 0 else ("NPT" if number % 2 else "Flanged"),
                "pressure_rating": "" if number % 9 == 0 else ("1200 WOG" if number % 17 == 0 else "600 WOG"),
                "temperature_range": "-20 C to 180 C",
                "certifications": "API 607; ISO 9001",
                "description": "Synthetic batch row for deterministic catalog-health demo.",
            }
            writer.writerow(row)
