"""Render a synthetic report as a PDF in one of several lab layouts, with its ground truth (plan 14.2 steps 2, 5).

Lab names are made up; layouts imitate common features of Indian lab reports (column orders, range headers,
H/L flags, SI units, date formats), not any real lab's template.
"""
from datetime import date

import pymupdf

from eval.generator.patients import TESTS, Patient, Report

NAMES = {  # three spellings per test; each layout uses a different one
    "4548-4": ["HbA1c", "Glycosylated Hemoglobin (HbA1c)", "HbA1c (Glycated Haemoglobin)"],
    "1558-6": ["Fasting Blood Sugar", "Glucose, Fasting (Plasma)", "FBS"],
    "3016-3": ["TSH", "Thyroid Stimulating Hormone (TSH)", "TSH - Ultrasensitive"],
    "3024-7": ["Free T4", "FT4", "Free Thyroxine (FT4)"],
    "718-7": ["Haemoglobin", "Hemoglobin (Hb)", "Hb"],
    "2093-3": ["Total Cholesterol", "Cholesterol, Total", "Serum Cholesterol"],
    "13457-7": ["LDL Cholesterol", "LDL Cholesterol (Calculated)", "LDL-C"],
    "2085-9": ["HDL Cholesterol", "HDL Cholesterol (Direct)", "HDL-C"],
    "2571-8": ["Triglycerides", "Serum Triglycerides", "TG"],
    "2160-0": ["Creatinine", "Serum Creatinine", "S. Creatinine"],
    "3084-1": ["Uric Acid", "Serum Uric Acid", "S. Uric Acid"],
    "1742-6": ["SGPT (ALT)", "ALT (SGPT)", "Alanine Aminotransferase"],
    "1920-8": ["SGOT (AST)", "AST (SGOT)", "Aspartate Aminotransferase"],
    "62292-8": ["25 OH Vitamin D", "Vitamin D (25-OH)", "Vitamin D Total"],
    "2132-9": ["Vitamin B12", "Vitamin B12 (Cyanocobalamin)", "Cobalamin"],
    "2951-2": ["Sodium", "Serum Sodium", "Sodium (Na+)"],
    "2823-3": ["Potassium", "Serum Potassium", "Potassium (K+)"],
    "2157-6": ["CPK", "Creatine Kinase (CK)", "CK - Total"],
}

# canonical = si * multiplier + offset (as in refdata/seed/unit_conversions.csv); decimals when printed in SI
SI = {
    "1558-6": ("mmol/L", 18.016, 0, 1), "2093-3": ("mmol/L", 38.67, 0, 2), "13457-7": ("mmol/L", 38.67, 0, 2),
    "2085-9": ("mmol/L", 38.67, 0, 2), "2571-8": ("mmol/L", 88.57, 0, 2), "2160-0": ("µmol/L", 0.011310, 0, 0),
    "3084-1": ("µmol/L", 0.016812, 0, 0), "62292-8": ("nmol/L", 0.40064, 0, 1), "2132-9": ("pmol/L", 1.3554, 0, 0),
    "718-7": ("g/L", 0.1, 0, 0), "4548-4": ("mmol/mol", 0.09152, 2.15, 0),
}

# name: (lab, columns as (header, x), name variant, date line, range style, flags, SI units)
LAYOUTS = {
    "classic": ("Sunrise Diagnostics", [("Test Name", 40), ("Result", 270), ("Unit", 340), ("Reference Range", 420)],
                0, "Collected on: {d:%d/%m/%Y}", "dash", False, False),
    "flags": ("CarePlus Path Lab", [("Test Description", 40), ("Observed Value", 270), ("Units", 360),
                                    ("Biological Ref. Interval", 430)], 1, "Sample Collected: {d:%d-%b-%Y}",
              "tight", True, False),
    "range_first": ("Medi-Scan Laboratories", [("Investigation", 40), ("Result", 260), ("Bio. Ref. Range", 330),
                                                ("Units", 470)], 2, "Collection Date: {d:%Y-%m-%d}", "dash", False,
                    False),
    "si_units": ("Arogya Labs", [("Test Name", 40), ("Result", 270), ("Unit", 340), ("Reference Range", 420)],
                 0, "Reg. Date: {d:%d.%m.%Y}", "dash", False, True),
}


def _fmt(x: float, decimals: int) -> str:
    return f"{x:.{decimals}f}"


def _printed(loinc: str, value: float, sex: str, si: bool) -> tuple[str, str, str | None, str | None]:
    """(value, unit, range low, range high) as printed."""
    spec = TESTS[loinc]
    low, high = spec.range_for(sex)
    if si and loinc in SI:
        unit, mult, offset, dec = SI[loinc]
        conv = lambda c: (c - offset) / mult  # noqa: E731
        return (_fmt(conv(value), dec), unit, None if low is None else _fmt(conv(low), dec),
                None if high is None else _fmt(conv(high), dec))
    # ranges are written as labs print them (4.0, 70, 0.7), so str() keeps their form
    return _fmt(value, spec.decimals), spec.unit, None if low is None else str(low), None if high is None else str(high)


def _range_text(low: str | None, high: str | None, style: str) -> str:
    if low is not None and high is not None:
        return f"{low} - {high}" if style == "dash" else f"{low}-{high}"
    if high is not None:
        return f"< {high}" if style == "dash" else f"Up to {high}"
    return f"> {low}"


def render_report(patient: Patient, report: Report, layout: str, doc_id: str,
                  today: date = date(2026, 10, 29)) -> tuple[bytes, dict]:
    lab, columns, variant, date_line, range_style, flags, si = LAYOUTS[layout]
    rows = []
    for loinc, value in report.values.items():
        v, unit, low, high = _printed(loinc, value, patient.sex, si)
        flag = None
        if flags:
            if low is not None and float(v) < float(low):
                flag = "L"
            elif high is not None and float(v) > float(high):
                flag = "H"
        rows.append({"loinc": loinc, "printed_name": NAMES[loinc][variant], "value": v, "unit": unit,
                     "range_low": low, "range_high": high, "range_text": _range_text(low, high, range_style),
                     "printed_flag": flag, "canonical_value": value, "canonical_unit": TESTS[loinc].unit})

    doc = pymupdf.open()
    page = doc.new_page()
    y = 50

    def line(text, x=40, size=10, font="helv"):
        page.insert_text((x, y), text, fontsize=size, fontname=font)

    line(lab, size=16, font="hebo")
    y += 16
    line("12, Example Road, Sector 4, New Delhi  |  NABL accredited (sample)", size=8)
    y += 24
    age = today.year - patient.birth_year
    line(f"Patient: {patient.display_name}    Age/Sex: {age} Y / {patient.sex[0].upper()}    Ref. by: Self")
    y += 14
    line(date_line.format(d=report.collected_on))
    y += 26
    for header, x in columns:
        line(header, x=x, font="hebo")
    y += 18
    for r in rows:
        cells = {"name": r["printed_name"], "value": r["value"] + (f"  {r['printed_flag']}" if r["printed_flag"] else ""),
                 "unit": r["unit"], "range": r["range_text"]}
        order = ["name", "value", "range", "unit"] if layout == "range_first" else ["name", "value", "unit", "range"]
        for key, (_, x) in zip(order, columns):
            line(cells[key], x=x)
        y += 16
    y += 20
    line("*** End of report ***", x=230, size=8)

    truth = {"doc_id": doc_id, "patient_key": patient.key, "kind": "lab_report", "layout": layout, "lab_name": lab,
             "collected_on": report.collected_on.isoformat(), "rows": rows}
    return doc.tobytes(), truth
