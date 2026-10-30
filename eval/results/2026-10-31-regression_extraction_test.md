# Extraction results (test split, v1)

A row is correct only if test, value, unit and range all match the printed report. Value, unit and range
columns are accuracies over rows whose test was found.

| Group | Docs | Rows | Precision | Recall | F1 | Value | Unit | Range | Date | Type |
|---|---|---|---|---|---|---|---|---|---|---|
| **All** | 46 | 208 | 97.6% | 97.6% | 97.6% | 100.0% | 97.6% | 100.0% | 100.0% | 100.0% |

## By format

| Group | Docs | Rows | Precision | Recall | F1 | Value | Unit | Range | Date | Type |
|---|---|---|---|---|---|---|---|---|---|---|
| pdf | 35 | 150 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| photo_clean | 4 | 20 | 90.0% | 90.0% | 90.0% | 100.0% | 90.0% | 100.0% | 100.0% | 100.0% |
| photo_degraded | 7 | 38 | 92.1% | 92.1% | 92.1% | 100.0% | 92.1% | 100.0% | 100.0% | 100.0% |

## By layout

| Group | Docs | Rows | Precision | Recall | F1 | Value | Unit | Range | Date | Type |
|---|---|---|---|---|---|---|---|---|---|---|
| classic | 9 | 42 | 95.2% | 95.2% | 95.2% | 100.0% | 95.2% | 100.0% | 100.0% | 100.0% |
| discharge | 5 | 0 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |
| flags | 12 | 62 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| range_first | 12 | 61 | 95.1% | 95.1% | 95.1% | 100.0% | 95.1% | 100.0% | 100.0% | 100.0% |
| si_units | 8 | 43 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

## Mistakes (5)

- didi_12_r02 (photo_degraded, range_first): Hb | 14.1 g/dL | 12.0 - 15.0  ->  read 14.1 7p/6 | 12.0 - 15.0
- nani_06_r02 (photo_clean, classic): Triglycerides | 111 mg/dL | < 150  ->  read 111 m9/6dl | < 150
- nani_06_r02 (photo_clean, classic): Haemoglobin | 14.6 g/dL | 12.0 - 15.0  ->  read 14.6 7p/6 | 12.0 - 15.0
- nani_06_r04 (photo_degraded, range_first): LDL-C | 88 mg/dL | < 100  ->  read 88 m99dlL | < 100
- nani_06_r04 (photo_degraded, range_first): Hb | 14.2 g/dL | 12.0 - 15.0  ->  read 14.2 7p/6 | 12.0 - 15.0
