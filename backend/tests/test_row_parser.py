import pytest

from app.services.labs.row_parser import RawRow, parse_line, parse_words


def row(name, value, unit=None, rng=None, flag=None):
    return RawRow(raw_name=name, raw_value=value, raw_unit=unit, raw_range=rng, printed_flag=flag)


# --- one line ------------------------------------------------------------------

@pytest.mark.parametrize("line,expected", [
    # typical digital report, columns joined with single spaces
    ("HbA1c (Glycosylated Haemoglobin) 7.2 % 4.0 - 5.6",
     row("HbA1c (Glycosylated Haemoglobin)", "7.2", "%", "4.0 - 5.6")),
    ("TSH 6.81 µIU/mL 0.35 - 5.50", row("TSH", "6.81", "µIU/mL", "0.35 - 5.50")),
    # OCR keeps two spaces between columns and glues cells
    ("HbA1c  7.2%  4.0 - 5.6", row("HbA1c", "7.2", "%", "4.0 - 5.6")),
    ("TSH  6.81  ulU/mL 0.35 - 5.50", row("TSH", "6.81", "ulU/mL", "0.35 - 5.50")),
    # range without spaces, en dash
    ("Haemoglobin 13.4 g/dL 13.0-17.0", row("Haemoglobin", "13.4", "g/dL", "13.0-17.0")),
    ("Potassium 4.1 mmol/L 3.5–5.1", row("Potassium", "4.1", "mmol/L", "3.5–5.1")),
    # range before unit
    ("Vitamin B12 410 211 - 911 pg/mL", row("Vitamin B12", "410", "pg/mL", "211 - 911")),
    # upper-limit range
    ("Total Cholesterol 212 mg/dL < 200", row("Total Cholesterol", "212", "mg/dL", "< 200")),
    ("Triglycerides 140 mg/dL <150", row("Triglycerides", "140", "mg/dL", "<150")),
    # printed H / L flags
    ("HbA1c 7.2 H % 4.0 - 5.6", row("HbA1c", "7.2", "%", "4.0 - 5.6", "H")),
    ("Vitamin D 25-OH 14.2 Low ng/mL 30 - 100", row("Vitamin D 25-OH", "14.2", "ng/mL", "30 - 100", "L")),
    # qualifier on value
    ("CRP <0.5 mg/L 0 - 5", row("CRP", "<0.5", "mg/L", "0 - 5")),
    # numbers inside the name
    ("25 OH Vitamin D 14.2 ng/mL 30 - 100", row("25 OH Vitamin D", "14.2", "ng/mL", "30 - 100")),
    ("Vitamin D 25 OH 14.2 ng/mL 30 - 100", row("Vitamin D 25 OH", "14.2", "ng/mL", "30 - 100")),
    # no range but a known unit
    ("Creatinine 1.1 mg/dL", row("Creatinine", "1.1", "mg/dL")),
    # no unit but a range
    ("INR 1.1 0.8 - 1.2", row("INR", "1.1", None, "0.8 - 1.2")),
])
def test_parse_line(line, expected):
    assert parse_line(line) == expected


@pytest.mark.parametrize("line", [
    "Test Name Result Unit Reference Range",
    "Sample Collected: 12/03/2026 09:15",
    "Age 58 Years",
    "Page 1 of 2",
    "Dr Demo Diagnostics, NABL Accredited",
    "Lab No 123456",
    "12/03/2026 7.2 % 4.0 - 5.6",  # name needs a real word, not just numbers
    "",
])
def test_non_result_lines_are_ignored(line):
    assert parse_line(line) is None


# --- a page of word boxes --------------------------------------------------------

def w(text, x0, y0, x1=None, y1=None):
    return {"text": text, "x0": x0, "y0": y0, "x1": x1 or x0 + 10 * len(text), "y1": y1 or y0 + 10}


def test_parse_words_groups_rows_and_returns_bbox():
    words = [
        # header row
        w("Test", 40, 100), w("Name", 80, 100), w("Result", 250, 100), w("Unit", 320, 100), w("Range", 400, 100),
        # a row whose cells are slightly misaligned vertically
        w("TSH", 40, 120), w("6.81", 250, 121), w("µIU/mL", 320, 119), w("0.35", 400, 120), w("-", 440, 120),
        w("5.50", 450, 120),
        w("HbA1c", 40, 140), w("7.2", 250, 140), w("%", 320, 140), w("4.0", 400, 140), w("-", 430, 140),
        w("5.6", 440, 140),
    ]
    rows = parse_words(words)
    assert [(r.raw_name, r.raw_value) for r in rows] == [("TSH", "6.81"), ("HbA1c", "7.2")]
    assert rows[0].bbox == {"x0": 40, "y0": 119, "x1": 490, "y1": 131}
