from __future__ import annotations

import re
from fractions import Fraction

from pint import UnitRegistry

from .models import NormalizedValue


ureg = UnitRegistry()

MATERIAL_ALIASES = {
    "ss304": "Stainless Steel 304",
    "ss 304": "Stainless Steel 304",
    "aisi 304": "Stainless Steel 304",
    "stainless steel 304": "Stainless Steel 304",
    "304 stainless steel": "Stainless Steel 304",
    "304 ss": "Stainless Steel 304",
    "ss316": "Stainless Steel 316",
    "ss 316": "Stainless Steel 316",
    "aisi 316": "Stainless Steel 316",
    "stainless steel 316": "Stainless Steel 316",
    "316 stainless steel": "Stainless Steel 316",
    "316 ss": "Stainless Steel 316",
    "brass": "Brass",
    "carbon steel": "Carbon Steel",
    "cast iron": "Cast Iron",
}


def _clean(raw: str) -> str:
    return re.sub(r"\s+", " ", raw.strip())


def _display_number(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:.3f}".rstrip("0").rstrip(".")


def _parse_fractional_number(value: str) -> float | None:
    value = value.strip()
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return None


def normalize_value(field: str, raw_value: str) -> tuple[NormalizedValue | None, str | None]:
    """Return a canonical value plus an explanation, keeping raw text outside this function."""
    raw = _clean(raw_value)
    if not raw:
        return None, None

    if field == "material":
        canonical = MATERIAL_ALIASES.get(raw.lower())
        if canonical:
            explanation = None if canonical == raw else f"Standardized material alias to {canonical}."
            return NormalizedValue(value=canonical, display=canonical), explanation
        return NormalizedValue(value=raw, display=raw), "Unrecognized material retained for review."

    if field == "size":
        scalar_size_pattern = r"(?:\d+(?:\.\d+)?|\d+\s*/\s*\d+)\s*(?:mm|millimet(?:er|re)s?|in(?:ch(?:es)?)?|\")"
        if re.search(r"(?:\bto\b|[-–])", raw, re.I) and len(re.findall(scalar_size_pattern, raw, re.I)) >= 2:
            return (
                NormalizedValue(value=raw, display=raw),
                "The source gives a product-family size range; select an individual SKU before assigning a scalar PIM size.",
            )
        dn_match = re.search(r"\bDN\s*(?P<number>\d{1,4})\b", raw, re.I)
        if dn_match:
            dn_size = int(dn_match.group("number"))
            dn_to_inch = {6: 0.125, 8: 0.25, 10: 0.375, 15: 0.5, 20: 0.75, 25: 1, 32: 1.25, 40: 1.5, 50: 2, 65: 2.5, 80: 3, 100: 4, 125: 5, 150: 6}
            if dn_size in dn_to_inch:
                inches = dn_to_inch[dn_size]
                return (
                    NormalizedValue(value=inches, unit="in", display=f"{_display_number(inches)} in"),
                    f"Mapped nominal {raw} to the corresponding inch designation; raw DN value is retained.",
                )
            return NormalizedValue(value=dn_size, unit="DN", display=f"DN {dn_size}"), "Retained nominal DN size for review."
        match = re.search(
            r"(?P<number>\d+(?:\.\d+)?|\d+\s*/\s*\d+)\s*(?P<unit>mm|millimet(?:er|re)s?|in(?:ch(?:es)?)?|\")",
            raw,
            re.I,
        )
        if not match:
            return None, "Could not parse a numeric size and supported unit."
        number = _parse_fractional_number(match.group("number").replace(" ", ""))
        if number is None or number <= 0:
            return None, "Size must be a positive numeric value."
        unit = match.group("unit").lower()
        if unit.startswith("mm") or unit.startswith("millimet"):
            inches = (number * ureg.millimeter).to(ureg.inch).magnitude
            return (
                NormalizedValue(value=round(inches, 4), unit="in", display=f"{_display_number(inches)} in"),
                f"Converted {raw} to inches for the PIM canonical size.",
            )
        return NormalizedValue(value=number, unit="in", display=f"{_display_number(number)} in"), None

    if field == "pressure_rating":
        pn_match = re.search(r"\bPN\s*(?P<number>\d+(?:\.\d+)?)\b", raw, re.I)
        if pn_match:
            number = float(pn_match.group("number"))
            return NormalizedValue(value=number, unit="PN", display=f"PN {_display_number(number)}"), "Retained the source nominal-pressure designation."
        class_match = re.search(r"\b(?:ASME\s+)?Class\s*(?P<number>\d+)\b", raw, re.I)
        if class_match:
            number = float(class_match.group("number"))
            return NormalizedValue(value=number, unit="ASME Class", display=f"ASME Class {_display_number(number)}"), "Retained the source pressure-class designation."
        wog_or_wsp = re.search(r"(?P<number>\d+(?:\.\d+)?)\s*(?:psi\s*)?(?P<unit>w\.?o\.?g\.?|w\.?s\.?p\.?)\b", raw, re.I)
        if wog_or_wsp:
            number = float(wog_or_wsp.group("number"))
            unit = wog_or_wsp.group("unit").lower().replace(".", "")
            canonical_unit = {"wog": "WOG", "wsp": "WSP"}[unit]
            return NormalizedValue(value=number, unit=canonical_unit, display=f"{_display_number(number)} {canonical_unit}"), (
                None if raw == f"{_display_number(number)} {canonical_unit}" else f"Standardized pressure notation to {canonical_unit}."
            )
        match = re.search(r"(?P<number>\d+(?:\.\d+)?)\s*(?P<unit>psi|bar)\b", raw, re.I)
        if not match:
            return None, "Could not parse a numeric pressure rating and supported unit."
        number = float(match.group("number"))
        unit = match.group("unit").lower().replace(".", "")
        canonical_unit = {"psi": "psi", "bar": "bar"}[unit]
        return NormalizedValue(value=number, unit=canonical_unit, display=f"{_display_number(number)} {canonical_unit}"), (
            None if raw == f"{_display_number(number)} {canonical_unit}" else f"Standardized pressure notation to {canonical_unit}."
        )

    if field == "temperature_range":
        match = re.search(
            r"(?P<low>[+-]?\d+(?:\.\d+)?)\s*°?\s*(?P<low_unit>[CF])\s*(?:to|[-–])\s*(?P<high>[+-]?\d+(?:\.\d+)?)\s*°?\s*(?P<high_unit>[CF])",
            raw,
            re.I,
        )
        if not match:
            return None, "Could not parse a numeric temperature range."
        low = float(match.group("low"))
        high = float(match.group("high"))
        low_unit = match.group("low_unit").upper()
        high_unit = match.group("high_unit").upper()
        if low_unit == "F":
            low = (low - 32) * 5 / 9
        if high_unit == "F":
            high = (high - 32) * 5 / 9
        if low > high:
            return None, "Temperature lower bound cannot exceed upper bound."
        display = f"{_display_number(low)} to {_display_number(high)} °C"
        explanation = None if raw.replace("°", "") == display.replace("°", "") else "Standardized the range to Celsius."
        return NormalizedValue(value=[round(low, 3), round(high, 3)], unit="°C", display=display), explanation

    if field == "end_connection":
        canonical = {"npt": "NPT", "bsp": "BSP", "flanged": "Flanged", "socket weld": "Socket Weld"}.get(raw.lower(), raw)
        return NormalizedValue(value=canonical, display=canonical), (
            None if canonical == raw else f"Standardized end-connection notation to {canonical}."
        )

    if field == "certifications":
        values = [part.strip().upper() for part in re.split(r"[,;/]", raw) if part.strip()]
        return NormalizedValue(value="; ".join(values), display="; ".join(values)), None

    if field == "product_type":
        canonical = raw.title()
        return NormalizedValue(value=canonical, display=canonical), None if canonical == raw else "Normalized product-type capitalization."

    return NormalizedValue(value=raw, display=raw), None


def infer_product_type(title: str) -> str | None:
    title_lower = title.lower()
    for phrase, canonical in (
        ("ball valve", "Ball Valve"),
        ("gate valve", "Gate Valve"),
        ("globe valve", "Globe Valve"),
        ("check valve", "Check Valve"),
        ("fitting", "Fitting"),
    ):
        if phrase in title_lower:
            return canonical
    return None


def normalized_key(value: NormalizedValue | None) -> str | None:
    if value is None:
        return None
    raw = value.value
    if isinstance(raw, list):
        return "|".join(str(item) for item in raw) + f"::{value.unit or ''}"
    return f"{str(raw).strip().lower()}::{value.unit or ''}"
