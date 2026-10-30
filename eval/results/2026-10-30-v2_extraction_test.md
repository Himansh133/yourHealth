# Extraction results (test split, v2)

A row is correct only if test, value, unit and range all match the printed report. Value, unit and range
columns are accuracies over rows whose test was found.

| Group | Docs | Rows | Precision | Recall | F1 | Value | Unit | Range | Date | Type |
|---|---|---|---|---|---|---|---|---|---|---|
| **All** | 43 | 186 | 97.2% | 93.0% | 95.1% | 100.0% | 98.9% | 100.0% | 100.0% | 100.0% |

## By format

| Group | Docs | Rows | Precision | Recall | F1 | Value | Unit | Range | Date | Type |
|---|---|---|---|---|---|---|---|---|---|---|
| pdf | 30 | 118 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| photo_clean | 8 | 39 | 93.5% | 74.4% | 82.9% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| photo_degraded | 5 | 29 | 89.7% | 89.7% | 89.7% | 100.0% | 92.9% | 100.0% | 100.0% | 100.0% |

## By layout

| Group | Docs | Rows | Precision | Recall | F1 | Value | Unit | Range | Date | Type |
|---|---|---|---|---|---|---|---|---|---|---|
| classic | 12 | 67 | 96.9% | 94.0% | 95.5% | 100.0% | 98.4% | 100.0% | 100.0% | 100.0% |
| discharge | 5 | 0 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |
| flags | 5 | 22 | 86.4% | 86.4% | 86.4% | 100.0% | 95.0% | 100.0% | 100.0% | 100.0% |
| range_first | 9 | 41 | 100.0% | 85.4% | 92.1% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| si_units | 12 | 56 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

## Mistakes (13)

- dada_04_r02 (photo_clean, range_first): not found: Alanine Aminotransferase | 38 U/L | 7 - 56
- dada_04_r02 (photo_clean, range_first): not found: Aspartate Aminotransferase | 22 U/L | 10 - 40
- dada_16_r02 (photo_degraded, classic): HDL Cholesterol | 42 mg/dL | > 40  ->  read 42 None | > 40
- dada_16_r04 (photo_clean, classic): not found: SGOT (AST) | 22 U/L | 10 - 40
- dada_16_r04 (photo_clean, classic): not found: CPK | 111 U/L | 30 - 200
- dada_16_r05 (photo_clean, range_first): not found: Alanine Aminotransferase | 40 U/L | 7 - 56
- dada_16_r05 (photo_clean, range_first): not found: Aspartate Aminotransferase | 22 U/L | 10 - 40
- dadi_15_r05 (photo_clean, flags): not found: Serum Creatinine | 1.11 mg/dL | 0.7-1.3  [unmapped rows: Serum Creatinine 1.11; Serum Uric Acid 5.2]
- dadi_15_r05 (photo_clean, flags): not found: Serum Uric Acid | 5.2 mg/dL | 3.5-7.2  [unmapped rows: Serum Creatinine 1.11; Serum Uric Acid 5.2]
- mummy_26_r02 (photo_clean, range_first): not found: Free Thyroxine (FT4) | 1.09 ng/dL | 0.8 - 1.8
- mummy_26_r05 (photo_clean, range_first): not found: Free Thyroxine (FT4) | 1.30 ng/dL | 0.8 - 1.8
- nana_05_r02 (photo_degraded, flags): Serum Uric Acid | 7.7 mg/dL | 3.5-7.2  ->  read 7.7 None | 3.5-7.2
- nani_18_r01 (photo_degraded, classic): not found: Haemoglobin | 14.3 g/dL | 12.0 - 15.0  [unmapped rows: Haemoglobin 14.3]
