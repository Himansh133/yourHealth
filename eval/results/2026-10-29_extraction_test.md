# Extraction results (test split, v1)

A row is correct only if test, value, unit and range all match the printed report. Value, unit and range
columns are accuracies over rows whose test was found.

| Group | Docs | Rows | Precision | Recall | F1 | Value | Unit | Range | Date | Type |
|---|---|---|---|---|---|---|---|---|---|---|
| **All** | 41 | 208 | 98.5% | 97.6% | 98.1% | 100.0% | 99.0% | 100.0% | 100.0% | 100.0% |

## By format

| Group | Docs | Rows | Precision | Recall | F1 | Value | Unit | Range | Date | Type |
|---|---|---|---|---|---|---|---|---|---|---|
| pdf | 30 | 150 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| photo_clean | 4 | 20 | 90.0% | 90.0% | 90.0% | 100.0% | 94.7% | 100.0% | 100.0% | 100.0% |
| photo_degraded | 7 | 38 | 97.2% | 92.1% | 94.6% | 100.0% | 97.2% | 100.0% | 100.0% | 100.0% |

## By layout

| Group | Docs | Rows | Precision | Recall | F1 | Value | Unit | Range | Date | Type |
|---|---|---|---|---|---|---|---|---|---|---|
| classic | 9 | 42 | 95.2% | 95.2% | 95.2% | 100.0% | 97.6% | 100.0% | 100.0% | 100.0% |
| flags | 12 | 62 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| range_first | 12 | 61 | 98.3% | 95.1% | 96.7% | 100.0% | 98.3% | 100.0% | 100.0% | 100.0% |
| si_units | 8 | 43 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

## Mistakes (5)

- didi_12_r02 (photo_degraded, range_first): not found: Hb | 14.1 g/dL | 12.0 - 15.0
- nani_06_r02 (photo_clean, classic): Triglycerides | 111 mg/dL | < 150  ->  read 111 m9/6dl | < 150
- nani_06_r02 (photo_clean, classic): not found: Haemoglobin | 14.6 g/dL | 12.0 - 15.0  [unmapped rows: Haemoglobin 14.6]
- nani_06_r04 (photo_degraded, range_first): LDL-C | 88 mg/dL | < 100  ->  read 88 m99dlL | < 100
- nani_06_r04 (photo_degraded, range_first): not found: Hb | 14.2 g/dL | 12.0 - 15.0
