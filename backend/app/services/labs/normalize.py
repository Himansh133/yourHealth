"""Turn a printed row into a normalised result with a flag and a confidence score (plan 7.3, 8.3, 8.4)."""
from dataclasses import dataclass
from decimal import Decimal

from app.services.labs.dictionary import LabDictionary, LabTest
from app.services.labs.row_parser import RawRow
from app.services.labs.values import compute_flag, convert, parse_range, parse_value

BASE_CONFIDENCE = 0.85  # plan 7.3, tier 2 (rule-based line parsing)
REVIEW_BELOW = 0.6
UNMAPPED_PENALTY = 0.2  # plan 7.3
# Larger than the plan's 0.2 so that either problem alone drops a row below REVIEW_BELOW;
# with 0.2 a misread "72" for "7.2" on a digital PDF would score 0.65 and skip review.
SANITY_PENALTY = 0.3
FLAG_MISMATCH_PENALTY = 0.3


@dataclass(frozen=True)
class NormalizedRow:
    raw: RawRow
    test: LabTest | None
    value_num: Decimal | None
    qualifier: str | None
    range_low: Decimal | None
    range_high: Decimal | None
    value_canonical: Decimal | None
    range_low_canonical: Decimal | None
    range_high_canonical: Decimal | None
    flag: str
    confidence: float


def normalize_row(raw: RawRow, d: LabDictionary, ocr_confidence: float | None = None) -> NormalizedRow:
    value, qualifier = parse_value(raw.raw_value)
    low, high = parse_range(raw.raw_range)
    # Flag in the raw unit against the range printed on this report: no unit conversion can disturb it.
    flag = compute_flag(value, low, high, qualifier)

    match = d.match(raw.raw_name)
    test = match.test if match else None
    conv = d.conversion(test.loinc_code, raw.raw_unit) if test and raw.raw_unit else None

    def to_canonical(x):
        return convert(x, *conv) if conv and x is not None else None

    value_canonical = to_canonical(value)

    confidence = BASE_CONFIDENCE * (ocr_confidence if ocr_confidence is not None else 1)
    if test is None:
        confidence -= UNMAPPED_PENALTY
    else:
        confidence -= (100 - match.score) / 100
    if value_canonical is not None and not (test.sanity_min <= value_canonical <= test.sanity_max):
        confidence -= SANITY_PENALTY
    printed = {"H": "high", "L": "low"}.get(raw.printed_flag)
    if printed and flag in ("low", "high", "normal") and printed != flag:
        confidence -= FLAG_MISMATCH_PENALTY

    return NormalizedRow(
        raw=raw,
        test=test,
        value_num=value,
        qualifier=qualifier,
        range_low=low,
        range_high=high,
        value_canonical=value_canonical,
        range_low_canonical=to_canonical(low),
        range_high_canonical=to_canonical(high),
        flag=flag,
        confidence=max(0.0, round(confidence, 4)),
    )
