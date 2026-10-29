# Extraction results (dev split, v1)

A row is correct only if test, value, unit and range all match the printed report. Value, unit and range
columns are accuracies over rows whose test was found.

| Group | Docs | Rows | Precision | Recall | F1 | Value | Unit | Range | Date | Type |
|---|---|---|---|---|---|---|---|---|---|---|
| **All** | 97 | 475 | 98.3% | 96.8% | 97.6% | 100.0% | 99.1% | 100.0% | 100.0% | 100.0% |

## By format

| Group | Docs | Rows | Precision | Recall | F1 | Value | Unit | Range | Date | Type |
|---|---|---|---|---|---|---|---|---|---|---|
| pdf | 66 | 330 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| photo_clean | 15 | 64 | 93.0% | 82.8% | 87.6% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| photo_degraded | 16 | 81 | 95.1% | 95.1% | 95.1% | 100.0% | 95.1% | 100.0% | 100.0% | 100.0% |

## By layout

| Group | Docs | Rows | Precision | Recall | F1 | Value | Unit | Range | Date | Type |
|---|---|---|---|---|---|---|---|---|---|---|
| classic | 27 | 117 | 100.0% | 96.6% | 98.3% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| flags | 25 | 134 | 94.0% | 93.3% | 93.6% | 100.0% | 96.9% | 100.0% | 100.0% | 100.0% |
| range_first | 25 | 120 | 100.0% | 98.3% | 99.2% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| si_units | 20 | 104 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

## Mistakes (15)

- chacha_19_r05 (photo_degraded, flags): Serum Uric Acid | 4.9 mg/dL | 3.5-7.2  ->  read 4.9 None | 3.5-7.2
- dada_04_r04 (photo_clean, classic): not found: SGOT (AST) | 22 U/L | 10 - 40
- dada_04_r04 (photo_clean, classic): not found: CPK | 108 U/L | 30 - 200
- dada_28_r01 (photo_degraded, flags): LDL Cholesterol (Calculated) | 159 mg/dL | Up to 100  ->  read 159 None | Up to 100
- dada_28_r01 (photo_degraded, flags): HDL Cholesterol (Direct) | 42 mg/dL | > 40  ->  read 42 None | >40
- dada_28_r01 (photo_degraded, flags): Creatine Kinase (CK) | 111 U/L | 30-200  ->  read 111 None | 30-200
- dada_28_r04 (photo_clean, classic): not found: SGOT (AST) | 22 U/L | 10 - 40
- dada_28_r04 (photo_clean, classic): not found: CPK | 110 U/L | 30 - 200
- dadi_03_r02 (photo_clean, flags): not found: Serum Creatinine | 1.00 mg/dL | 0.7-1.3  [unmapped rows: Serum Creatinine 1.00; Serum Uric Acid 5.0]
- dadi_03_r02 (photo_clean, flags): not found: Serum Uric Acid | 5.0 mg/dL | 3.5-7.2  [unmapped rows: Serum Creatinine 1.00; Serum Uric Acid 5.0]
- mausi_10_r02 (photo_clean, flags): not found: Serum Triglycerides | 163 mg/dL | Up to 150  [unmapped rows: Serum Triglycerides 163 H]
- mausi_10_r02 (photo_clean, flags): not found: AST (SGOT) | 22 U/L | 10-40  [unmapped rows: Serum Triglycerides 163 H]
- mummy_14_r03 (photo_clean, range_first): not found: Free Thyroxine (FT4) | 1.24 ng/dL | 0.8 - 1.8
- nani_18_r03 (photo_clean, range_first): not found: Hb | 13.7 g/dL | 12.0 - 15.0
- papa_01_r03 (photo_clean, flags): not found: Serum Uric Acid | 5.0 mg/dL | 3.5-7.2  [unmapped rows: Serum Uric Acid 5.0]
