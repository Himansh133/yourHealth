# Reference data sources

Every file in `seed/` and where it came from. Update this when you add or verify data.

| File | Source | Licence | Status |
|---|---|---|---|
| `seed/lab_tests.csv` | LOINC codes from the implementation plan, section 8.1 | LOINC: free, needs loinc.org account and licence acceptance | **Not yet verified on loinc.org** (plan section 19) |
| `seed/aliases.csv` | Written by the team from common Indian lab report spellings | Ours | Grow it from synthetic layouts and permitted real reports |
| `seed/lab_tests.csv` sanity_min/max | Team-written plausibility bounds in canonical units, deliberately wide; only used to lower extraction confidence | Ours | Review with faculty mentor |
| `seed/unit_conversions.csv` | Plan section 8.3 (molar masses and IFCC/NGSP formula) | n/a | HbA1c check: 53 mmol/mol -> 7.00 % (tested) |

`display_name_hi` values are plain spoken-Hindi glosses written by the team; have a Hindi speaker review them.

## Medicines

| File | Source | Licence | Status |
|---|---|---|---|
| `seed/drug_ingredients.csv` | Team list of common chronic medicines in India; ATC codes from the WHO ATC index | WHO ATC: check terms before bulk use | ATC codes **not yet checked** against whocc.no |
| `seed/drug_brands.csv` | 41 common Indian brands, typed by the team (`source=manual`). Manufacturer left blank on purpose | Facts (brand -> composition) only | **Verify each composition** against the pack or the Jan Aushadhi / CDSCO lists before the demo. The plan's Kaggle dataset can replace this later (licence unclear: academic demo only) |
| `seed/name_map_in_us.csv` | Plan section 9.2 (Indian vs US generic names) | n/a | |
| `seed/drug_labels.jsonl` | openFDA Drug Label API (api.fda.gov/drug/label.json), one label per ingredient: single ingredient, oral, prescription preferred, newest. Each record has its DailyMed set id, URL and fetch date | Public domain | Regenerate with `python -m app.refdata.fetch_openfda`. Vildagliptin has no US label; cholecalciferol has no single-ingredient label |
| `seed/drug_lab_effects.csv` | Plan section 9.4 seed rows; each row cites a label section and an evidence phrase | Ours, citing public-domain labels | 32/32 rows **supported** by label text (see `EFFECTS_VERIFICATION.md`). Still needs a human read and faculty review (`reviewed_by`) |

Only generic drug names are ever sent to openFDA, at load time. No patient data.

