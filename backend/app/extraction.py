from __future__ import annotations

import csv
import io
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

import pymupdf

from .config import MAX_UPLOAD_BYTES, UPLOAD_DIR
from .models import Evidence


FIELD_ORDER = [
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

FIELD_ALIASES = {
    "manufacturer": ["manufacturer", "brand", "maker", "supplier"],
    "manufacturer_part_number": ["manufacturer part number", "part number", "part no", "mpn", "sku", "model number", "model", "stock number"],
    "product_title": ["product title", "product name", "title", "name", "series"],
    "product_type": ["product type", "valve type", "type"],
    "material": ["material", "body material", "material of construction"],
    "size": ["size", "nominal size", "nominal diameter", "diameter", "pipe size", "port size"],
    "end_connection": ["end connection", "end connections", "connection", "connection type", "end type"],
    "pressure_rating": ["pressure rating", "nominal pressure", "working pressure", "pressure class", "pressure", "rating"],
    "temperature_range": ["temperature range", "temperature", "temp range", "operating temperature"],
    "certifications": ["certifications", "certification", "standards"],
    "description": ["description", "product description"],
}

OCR_PAGE_LIMIT = 8
OCR_TEXT_THRESHOLD = 24

PRODUCT_HEADING_PATTERN = re.compile(r"\b(?:ball|gate|globe|check|butterfly|plug)\s+valves?\b|\bfittings?\b", re.I)
PRODUCT_TYPE_PATTERN = re.compile(r"\b(?P<type>ball|gate|globe|check|butterfly|plug)\s+valves?\b|\b(?P<fitting>fittings?)\b", re.I)
MATERIAL_PATTERN = re.compile(
    r"\b(?:stainless\s+steel\s*(?:30[46]|316l)?|(?:30[46]|316l?)\s*(?:stainless\s+steel|ss)|carbon\s+steel|brass|bronze|cast\s+iron|pvc)\b",
    re.I,
)
SIZE_PATTERN = re.compile(
    r"\b(?:DN\s*\d{1,4}\b|(?:\d+(?:\.\d+)?|\d+\s*/\s*\d+)\s*(?:mm|millimet(?:er|re)s?|in(?:ch(?:es)?)?|\")\s*(?:to|[-–])\s*(?:\d+(?:\.\d+)?|\d+\s*/\s*\d+)\s*(?:mm|millimet(?:er|re)s?|in(?:ch(?:es)?)?|\")|(?:\d+(?:\.\d+)?|\d+\s*/\s*\d+)\s*(?:mm|millimet(?:er|re)s?|in(?:ch(?:es)?)?|\"))",
    re.I,
)
CONNECTION_PATTERN = re.compile(r"\b(?:npt|bsp(?:t|p)?|flanged|tri[ -]?clamp|socket\s+weld|butt\s+weld|threaded|screwed)\b", re.I)
PRESSURE_PATTERN = re.compile(r"\b(?:PN\s*\d+|(?:ASME\s+)?Class\s*\d+|\d+(?:\.\d+)?\s*(?:(?:psi\s*)?(?:w\.?o\.?g\.?|w\.?s\.?p\.?)|psi|bar))\b", re.I)
TEMPERATURE_PATTERN = re.compile(r"[+-]?\d+(?:\.\d+)?\s*°?\s*[CF]\s*(?:to|[-–])\s*[+-]?\d+(?:\.\d+)?\s*°?\s*[CF]", re.I)
CERTIFICATION_PATTERN = re.compile(r"\b(?:API\s*\d+|ASME\s*[A-Z]?\d+[\w.-]*|ISO\s*\d+[\w.-]*|CE|ATEX|3-A)\b", re.I)
LEGAL_ENTITY_PATTERN = re.compile(
    r"\b([A-Z][\w&.-]*(?:\s+[A-Z][\w&.-]*){0,4},?\s+(?:GmbH|Corporation|Inc\.?|LLC|Ltd\.?|Limited|S\.A\.))\b"
)


@dataclass
class Candidate:
    raw_value: str
    evidence: Evidence
    inferred: bool = False


@dataclass
class SourceRow:
    source_file: str
    source_kind: str
    candidates: dict[str, list[Candidate]] = field(default_factory=dict)
    context: str = ""


class SourceReadError(ValueError):
    pass


def is_synthetic_name(filename: str) -> bool:
    return "synthetic" in filename.lower()


def safely_store_upload(filename: str, payload: bytes) -> None:
    if len(payload) > MAX_UPLOAD_BYTES:
        raise SourceReadError(f"{filename} is larger than the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB demo limit.")
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename).name)
    (UPLOAD_DIR / safe_name).write_bytes(payload)


def _canonical_header(header: str) -> str | None:
    compact = _compact_label(header)
    for field, aliases in FIELD_ALIASES.items():
        if compact in aliases:
            return field
    return None


def _compact_label(value: str) -> str:
    without_parentheses = re.sub(r"\([^)]*\)", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", without_parentheses.lower()).strip()


def _add_candidate(row: SourceRow, field: str, raw: str, evidence: Evidence, inferred: bool = False) -> None:
    value = str(raw).strip()
    if value:
        row.candidates.setdefault(field, []).append(Candidate(value, evidence, inferred=inferred))


def _page_lines(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if re.sub(r"\s+", " ", line).strip()]


def _field_for_label(value: str) -> str | None:
    return _canonical_header(value.rstrip(":=-–— "))


def _next_value(lines: list[str], index: int) -> str | None:
    for candidate in lines[index + 1 : index + 4]:
        if _field_for_label(candidate):
            return None
        if len(candidate) <= 240:
            return candidate
    return None


def _add_unique_candidate(row: SourceRow, field: str, candidate: Candidate) -> None:
    existing = row.candidates.setdefault(field, [])
    marker = candidate.raw_value.strip().lower()
    for index, present in enumerate(existing):
        if present.raw_value.strip().lower() == marker:
            if present.inferred and not candidate.inferred:
                existing[index] = candidate
            return
    existing.append(candidate)


def _add_structural_candidate(
    row: SourceRow,
    field: str,
    raw_value: str,
    filename: str,
    page: int,
    snippet: str,
    method: str,
    *,
    inferred: bool,
) -> None:
    value = raw_value.strip()
    if not value:
        return
    _add_unique_candidate(
        row,
        field,
        Candidate(
            value,
            Evidence(source_file=filename, page=page, snippet=snippet[:500], method=method),
            inferred=inferred,
        ),
    )


def _extract_labeled_text(text: str, filename: str, page: int, method: str = "pdf_text_extraction") -> SourceRow:
    result = SourceRow(filename, "synthetic_demo" if is_synthetic_name(filename) else "uploaded", context=text)
    for compact in _page_lines(text):
        parsed = _explicit_label_value(compact)
        if parsed:
            field, raw_value = parsed
            _add_structural_candidate(result, field, raw_value, filename, page, compact, method, inferred=False)
    return result


def _explicit_label_value(line: str) -> tuple[str, str] | None:
    """Return a trusted label/value pair only when an explicit delimiter is present."""
    for separator in (":", "=", "#"):
        if separator not in line:
            continue
        label, raw_value = line.split(separator, 1)
        field = _field_for_label(label)
        if field and raw_value.strip():
            return field, raw_value.strip()
    return None


def _extract_labelled_product_blocks(
    page_texts: list[tuple[int, str]], filename: str, page_methods: dict[int, str]
) -> list[SourceRow]:
    """Split repeated explicitly-labelled product cards at a second part-number label.

    This intentionally requires a product identifier on every segment. Without that
    boundary, merging a family manual into individual SKUs would be unsafe.
    """
    records: list[SourceRow] = []
    current = SourceRow(filename, "synthetic_demo" if is_synthetic_name(filename) else "uploaded")
    pending_manufacturer: tuple[int, str, str, str] | None = None

    def add_pending_manufacturer(target: SourceRow) -> None:
        nonlocal pending_manufacturer
        if not pending_manufacturer:
            return
        pending_page, pending_value, pending_line, pending_method = pending_manufacturer
        _add_structural_candidate(
            target,
            "manufacturer",
            pending_value,
            filename,
            pending_page,
            pending_line,
            pending_method,
            inferred=False,
        )
        target.context += ("\n" if target.context else "") + pending_line
        pending_manufacturer = None

    for page, text in page_texts:
        method = page_methods.get(page, "pdf_text_extraction")
        for line in _page_lines(text):
            parsed = _explicit_label_value(line)
            if not parsed:
                continue
            field, raw_value = parsed
            # Supplier catalog cards commonly print a repeated manufacturer line
            # immediately before the next part number. Hold that one line until the
            # boundary is known so it belongs to the upcoming SKU, not the prior one.
            if field == "manufacturer" and current.candidates.get("manufacturer_part_number"):
                pending_manufacturer = (page, raw_value, line, method)
                continue
            if field == "manufacturer_part_number" and current.candidates.get("manufacturer_part_number"):
                records.append(current)
                current = SourceRow(filename, "synthetic_demo" if is_synthetic_name(filename) else "uploaded")
                add_pending_manufacturer(current)
            elif pending_manufacturer:
                add_pending_manufacturer(current)
            _add_structural_candidate(current, field, raw_value, filename, page, line, method, inferred=False)
            current.context += ("\n" if current.context else "") + line
    add_pending_manufacturer(current)
    if current.candidates.get("manufacturer_part_number"):
        records.append(current)
    return records if len(records) >= 2 else []


def _table_cells(line: str) -> list[str]:
    """Split a visually simple PDF table row without guessing arbitrary prose columns."""
    stripped = line.strip()
    if "|" in stripped:
        return [cell.strip() for cell in stripped.split("|")]
    if "\t" in stripped:
        return [cell.strip() for cell in stripped.split("\t")]
    return [cell.strip() for cell in re.split(r"\s{2,}", stripped)]


def _extract_pdf_catalog_rows(text: str, filename: str, page: int, method: str) -> list[SourceRow]:
    """Read explicit header/row tables into isolated SKU candidates.

    A table is used only when its header establishes at least three known fields and
    a product identifier, title, or type. This avoids treating ordinary prose or a
    manual's two-column layout as a product table.
    """
    raw_lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    rows: list[SourceRow] = []
    for header_index, header_line in enumerate(raw_lines):
        header_cells = _table_cells(header_line)
        if len(header_cells) < 3:
            continue
        fields = [_canonical_header(cell) for cell in header_cells]
        recognized = [field for field in fields if field]
        if len(set(recognized)) < 3:
            continue
        if not any(field in {"manufacturer_part_number", "product_title", "product_type"} for field in recognized):
            continue
        for data_line in raw_lines[header_index + 1 : header_index + 31]:
            cells = _table_cells(data_line)
            if len(cells) != len(header_cells) or len(cells) < 3:
                break
            if sum(_canonical_header(cell) is not None for cell in cells) >= 3:
                break
            record = SourceRow(
                filename,
                "synthetic_demo" if is_synthetic_name(filename) else "uploaded",
                context=f"{header_line}\n{data_line}",
            )
            for field, value in zip(fields, cells):
                if field and value:
                    _add_structural_candidate(
                        record,
                        field,
                        value,
                        filename,
                        page,
                        f"{header_line} | {data_line}",
                        "pdf_table_row_extraction" if method == "pdf_text_extraction" else method,
                        inferred=False,
                    )
            identifier_fields = ("manufacturer_part_number", "product_title", "product_type")
            if sum(bool(record.candidates.get(field)) for field in identifier_fields) and len(record.candidates) >= 3:
                rows.append(record)
        if rows:
            break
    return rows


def _best_product_heading(lines: list[str]) -> str | None:
    frequency = {line: lines.count(line) for line in set(lines)}
    candidates: list[tuple[int, str]] = []
    for line in lines:
        if not PRODUCT_HEADING_PATTERN.search(line) or len(line) > 110 or line.endswith((".", ";", ",")):
            continue
        lowered = line.lower()
        if any(
            blocked in lowered
            for blocked in (
                "instruction", "installation", "operation", "maintenance", "contents", "page ", "before using",
                "using an", "must be", "read and", "all series", " are ", "listed", "tested", "rated",
            )
        ):
            continue
        score = 0
        product_type = PRODUCT_TYPE_PATTERN.search(line)
        if product_type:
            score += 4
            if product_type.end() == len(line):
                score += 3
        if line == line.title() or re.search(r"\b[A-Z]{2,}\b", line):
            score += 2
        score += min(frequency[line], 4)
        score -= len(line) // 45
        candidates.append((score, line))
    return max(candidates, default=(0, ""), key=lambda item: item[0])[1] or None


def _spanned_field_label(lines: list[str], index: int, allowed_fields: set[str]) -> tuple[str, int] | None:
    """Recognise a table header split over up to three extracted PDF lines."""
    for span in (3, 2, 1):
        if index + span > len(lines):
            continue
        field = _field_for_label(" ".join(lines[index : index + span]))
        if field in allowed_fields:
            return field, index + span
    return None


def _extract_compact_spec_grid(
    result: SourceRow,
    lines: list[str],
    filename: str,
    page: int,
    method: str,
    field_patterns: dict[str, re.Pattern[str]],
) -> None:
    """Recover a product-family spec grid whose headers wrap across PDF text lines.

    This reads only a short run of known column headers followed by the first
    matching value for each header. It therefore improves ordinary manufacturer
    datasheets without turning a series table into invented individual SKUs.
    """
    headers: list[tuple[int, int, str]] = []
    allowed_fields = set(field_patterns)
    for index in range(len(lines)):
        matched = _spanned_field_label(lines, index, allowed_fields)
        if matched:
            field, end = matched
            headers.append((index, end, field))

    for header_start, _, _ in headers:
        nearby = [header for header in headers if header_start <= header[0] < header_start + 14]
        fields = {field for _, _, field in nearby}
        if len(fields) < 3:
            continue
        value_start = max(end for _, end, _ in nearby)
        values = lines[value_start : value_start + 20]
        if not values:
            continue
        found_fields: set[str] = set()
        for value in values:
            for field, pattern in field_patterns.items():
                if field not in fields or field in found_fields:
                    continue
                match = pattern.search(value)
                if not match:
                    continue
                raw_value = value if field == "end_connection" else match.group(0)
                _add_structural_candidate(
                    result,
                    field,
                    raw_value,
                    filename,
                    page,
                    f"spec grid: {field.replace('_', ' ')} | {value}",
                    method,
                    inferred=True,
                )
                found_fields.add(field)
        if found_fields:
            return


def _canonical_product_type(raw_value: str) -> str:
    return re.sub(r"\bvalves\b", "Valve", raw_value, flags=re.I).rstrip("s")


def _extract_structural_pdf_text(text: str, filename: str, page: int, method: str) -> SourceRow:
    """Recover safe, review-required candidates from table-like manufacturer PDF layouts."""
    result = SourceRow(filename, "synthetic_demo" if is_synthetic_name(filename) else "uploaded", context=text)
    lines = _page_lines(text)
    field_patterns = {
        "material": MATERIAL_PATTERN,
        "size": SIZE_PATTERN,
        "end_connection": CONNECTION_PATTERN,
        "pressure_rating": PRESSURE_PATTERN,
        "temperature_range": TEMPERATURE_PATTERN,
        "certifications": CERTIFICATION_PATTERN,
    }
    _extract_compact_spec_grid(result, lines, filename, page, method, field_patterns)
    for index, label in enumerate(lines):
        field = _field_for_label(label)
        if not field or field not in field_patterns:
            continue
        value = _next_value(lines, index)
        if not value:
            continue
        match = field_patterns[field].search(value)
        if match:
            _add_structural_candidate(
                result,
                field,
                match.group(0),
                filename,
                page,
                f"{label} | {value}",
                method,
                inferred=True,
            )
    return result


def _extract_document_identity(page_texts: list[tuple[int, str]], filename: str) -> SourceRow:
    """Identify a product family and maker once per document, never once per repeating page header."""
    combined_lines = [line for _, text in page_texts for line in _page_lines(text)]
    result = SourceRow(filename, "synthetic_demo" if is_synthetic_name(filename) else "uploaded")
    title = _best_product_heading(combined_lines)
    if title:
        page = next(page_number for page_number, text in page_texts if title in text)
        _add_structural_candidate(result, "product_title", title, filename, page, title, "pdf_layout_inference", inferred=True)
        product_type = PRODUCT_TYPE_PATTERN.search(title)
        if product_type:
            _add_structural_candidate(
                result,
                "product_type",
                _canonical_product_type(product_type.group(0)),
                filename,
                page,
                title,
                "pdf_layout_inference",
                inferred=True,
            )

    entities: list[tuple[str, int]] = []
    for page_number, text in page_texts:
        entities.extend((match.group(1), page_number) for match in LEGAL_ENTITY_PATTERN.finditer(text))
    if entities:
        counts = {entity: sum(candidate == entity for candidate, _ in entities) for entity, _ in entities}
        manufacturer = max(counts, key=lambda entity: (counts[entity], len(entity)))
        page = next(page_number for entity, page_number in entities if entity == manufacturer)
        _add_structural_candidate(result, "manufacturer", manufacturer, filename, page, manufacturer, "pdf_layout_inference", inferred=True)
    return result


def _ocr_page_text(page: pymupdf.Page) -> str:
    """Best-effort local OCR for scanned pages; absence/failure remains a safe no-result."""
    tesseract = shutil.which("tesseract")
    if not tesseract:
        return ""
    try:
        with tempfile.TemporaryDirectory(prefix="vericatalog-ocr-") as directory:
            image_path = Path(directory) / "page.png"
            page.get_pixmap(matrix=pymupdf.Matrix(2, 2), colorspace=pymupdf.csGRAY, alpha=False).save(image_path)
            completed = subprocess.run(
                [tesseract, str(image_path), "stdout", "-l", "eng", "--psm", "6"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            return completed.stdout.strip() if completed.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _merge_pdf_row(target: SourceRow, source: SourceRow) -> None:
    for field, candidates in source.candidates.items():
        for candidate in candidates:
            _add_unique_candidate(target, field, candidate)


def _merge_missing_pdf_identity(target: SourceRow, identity: SourceRow) -> None:
    """Add document-level context only where an isolated SKU row has no source value."""
    for field, candidates in identity.candidates.items():
        if target.candidates.get(field):
            continue
        for candidate in candidates:
            _add_unique_candidate(target, field, candidate)


def parse_pdf(filename: str, payload: bytes) -> list[SourceRow]:
    try:
        document = pymupdf.open(stream=payload, filetype="pdf")
    except Exception as exc:  # PyMuPDF messages vary by version.
        raise SourceReadError(f"Could not read {filename} as a PDF.") from exc
    merged = SourceRow(filename, "synthetic_demo" if is_synthetic_name(filename) else "uploaded")
    page_texts: list[tuple[int, str]] = []
    page_methods: dict[int, str] = {}
    catalog_rows: list[SourceRow] = []
    ocr_pages_checked = 0
    ocr_available = shutil.which("tesseract") is not None
    for index, page in enumerate(document, start=1):
        text = page.get_text("text").strip()
        method = "pdf_text_extraction"
        if len(text) < OCR_TEXT_THRESHOLD and ocr_available and ocr_pages_checked < OCR_PAGE_LIMIT:
            ocr_text = _ocr_page_text(page)
            if ocr_text:
                text = ocr_text
                method = "pdf_ocr_extraction"
            ocr_pages_checked += 1
        if not text:
            continue
        page_texts.append((index, text))
        page_methods[index] = method
        catalog_rows.extend(_extract_pdf_catalog_rows(text, filename, index, method))
        labelled = _extract_labeled_text(text, filename, index, method)
        structural = _extract_structural_pdf_text(
            text,
            filename,
            index,
            "pdf_layout_inference" if method == "pdf_text_extraction" else method,
        )
        _merge_pdf_row(merged, labelled)
        _merge_pdf_row(merged, structural)
        merged.context += ("\n" if merged.context else "") + text
    document.close()
    identity = _extract_document_identity(page_texts, filename)
    segmented_rows = catalog_rows or _extract_labelled_product_blocks(page_texts, filename, page_methods)
    if segmented_rows:
        for row in segmented_rows:
            _merge_missing_pdf_identity(row, identity)
        return segmented_rows
    _merge_pdf_row(merged, identity)
    if not merged.candidates:
        raise SourceReadError(
            f"{filename} contains no identifiable valve/fitting attribute text. The local parser checked embedded text"
            f" and {'attempted OCR on low-text pages' if ocr_pages_checked else 'local OCR is unavailable or was not needed'}; use a product document with"
            " identifiable product context or a spreadsheet with field headers."
        )
    return [merged]


def parse_csv(filename: str, payload: bytes) -> list[SourceRow]:
    try:
        text = payload.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
    except UnicodeDecodeError as exc:
        raise SourceReadError(f"{filename} must be UTF-8 encoded.") from exc
    if not reader.fieldnames:
        raise SourceReadError(f"{filename} is empty or has no header row.")
    headers = {header: _canonical_header(header) for header in reader.fieldnames}
    if not any(headers.values()):
        raise SourceReadError(f"{filename} has no recognized valve/fitting headers.")
    rows: list[SourceRow] = []
    source_kind = "synthetic_demo" if is_synthetic_name(filename) else "uploaded"
    for row_number, values in enumerate(reader, start=2):
        if not any(str(value or "").strip() for value in values.values()):
            continue
        parsed = SourceRow(filename, source_kind)
        for header, field in headers.items():
            if field and values.get(header):
                raw = str(values[header]).strip()
                _add_candidate(
                    parsed,
                    field,
                    raw,
                    Evidence(source_file=filename, row=row_number, snippet=f"{header}: {raw}"[:500], method="csv_row_extraction"),
                )
        parsed.context = "\n".join(
            f"{header}: {str(value).strip()}" for header, value in values.items() if str(value or "").strip()
        )
        if parsed.candidates:
            rows.append(parsed)
    if not rows:
        raise SourceReadError(f"{filename} has no non-empty product rows.")
    return rows


def _xlsx_cell_text(cell: ET.Element, shared_strings: list[str], namespace: str) -> str:
    cell_type = cell.attrib.get("t")
    value = cell.find(f"{namespace}v")
    if value is None or value.text is None:
        inline = cell.find(f"{namespace}is/{namespace}t")
        return inline.text if inline is not None and inline.text else ""
    if cell_type == "s":
        try:
            return shared_strings[int(value.text)]
        except (IndexError, ValueError):
            return ""
    return value.text


def _xlsx_column_index(reference: str) -> int:
    """Convert XLSX cell references such as B3 to a zero-based column index."""
    letters = re.match(r"[A-Z]+", reference)
    if not letters:
        return 0
    index = 0
    for letter in letters.group(0):
        index = index * 26 + (ord(letter) - ord("A") + 1)
    return index - 1


def parse_xlsx(filename: str, payload: bytes) -> list[SourceRow]:
    """Read a simple first-sheet XLSX without requiring an extra Excel engine."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
        shared_strings: list[str] = []
        namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = ["".join(node.itertext()) for node in root.findall(f"{namespace}si")]
        sheet_name = "xl/worksheets/sheet1.xml"
        if sheet_name not in archive.namelist():
            raise SourceReadError(f"{filename} has no readable first worksheet.")
        root = ET.fromstring(archive.read(sheet_name))
    except (zipfile.BadZipFile, ET.ParseError) as exc:
        raise SourceReadError(f"Could not read {filename} as a simple XLSX workbook.") from exc
    sparse_rows: list[dict[int, str]] = []
    width = 0
    for sheet_row in root.findall(f".//{namespace}sheetData/{namespace}row"):
        values: dict[int, str] = {}
        for fallback_index, cell in enumerate(sheet_row.findall(f"{namespace}c")):
            column_index = _xlsx_column_index(cell.attrib.get("r", "")) if cell.attrib.get("r") else fallback_index
            values[column_index] = _xlsx_cell_text(cell, shared_strings, namespace)
            width = max(width, column_index + 1)
        sparse_rows.append(values)
    matrix = [[row.get(index, "") for index in range(width)] for row in sparse_rows]
    if len(matrix) < 2:
        raise SourceReadError(f"{filename} needs a header row and at least one product row.")
    headers = matrix[0]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(matrix)
    return parse_csv(filename, output.getvalue().encode("utf-8"))


def parse_source_payload(filename: str, payload: bytes) -> list[SourceRow]:
    """Parse source bytes without persisting them, for controlled local evaluation."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(filename, payload)
    if suffix == ".csv":
        return parse_csv(filename, payload)
    if suffix == ".xlsx":
        return parse_xlsx(filename, payload)
    raise SourceReadError("Supported file types are PDF, CSV, and XLSX.")


def parse_source(filename: str, payload: bytes) -> list[SourceRow]:
    """Persist a user upload for the local app, then parse it."""
    safely_store_upload(filename, payload)
    return parse_source_payload(filename, payload)


def manual_source(title: str | None, part_number: str | None) -> SourceRow | None:
    if not (title or part_number):
        return None
    row = SourceRow("Manual entry", "manual")
    if title and title.strip():
        _add_candidate(
            row,
            "product_title",
            title,
            Evidence(source_file="Manual entry", snippet=title.strip(), method="manual_input"),
        )
    if part_number and part_number.strip():
        _add_candidate(
            row,
            "manufacturer_part_number",
            part_number,
            Evidence(source_file="Manual entry", snippet=part_number.strip(), method="manual_input"),
        )
    row.context = "\n".join(candidate.raw_value for candidates in row.candidates.values() for candidate in candidates)
    return row
