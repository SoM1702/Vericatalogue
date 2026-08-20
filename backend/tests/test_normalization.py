from app.normalization import normalize_value


def test_normalizes_metric_size_to_inches() -> None:
    normalized, explanation = normalize_value("size", "25.4 mm")
    assert normalized is not None
    assert normalized.value == 1.0
    assert normalized.unit == "in"
    assert normalized.display == "1 in"
    assert explanation is not None


def test_normalizes_material_alias() -> None:
    normalized, explanation = normalize_value("material", "SS304")
    assert normalized is not None
    assert normalized.display == "Stainless Steel 304"
    assert explanation == "Standardized material alias to Stainless Steel 304."


def test_normalizes_pressure_and_temperature() -> None:
    pressure, pressure_note = normalize_value("pressure_rating", "600 w.o.g.")
    temperature, temperature_note = normalize_value("temperature_range", "-20 C to 180 C")
    assert pressure is not None and pressure.display == "600 WOG"
    assert pressure_note is not None
    assert temperature is not None and temperature.value == [-20.0, 180.0]
    assert temperature_note is not None


def test_normalizes_dn_size_and_nominal_pressure() -> None:
    size, size_note = normalize_value("size", "DN 25")
    pressure, pressure_note = normalize_value("pressure_rating", "PN 16")
    assert size is not None and size.display == "1 in"
    assert size_note is not None
    assert pressure is not None and pressure.display == "PN 16"
    assert pressure_note is not None
