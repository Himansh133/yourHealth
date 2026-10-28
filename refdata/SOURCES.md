# Reference data sources

Every file in `seed/` and where it came from. Update this when you add or verify data.

| File | Source | Licence | Status |
|---|---|---|---|
| `seed/lab_tests.csv` | LOINC codes from the implementation plan, section 8.1 | LOINC: free, needs loinc.org account and licence acceptance | **Not yet verified on loinc.org** (plan section 19) |
| `seed/aliases.csv` | Written by the team from common Indian lab report spellings | Ours | Grow it from synthetic layouts and permitted real reports |
| `seed/lab_tests.csv` sanity_min/max | Team-written plausibility bounds in canonical units, deliberately wide; only used to lower extraction confidence | Ours | Review with faculty mentor |
| `seed/unit_conversions.csv` | Plan section 8.3 (molar masses and IFCC/NGSP formula) | n/a | HbA1c check: 53 mmol/mol -> 7.00 % (tested) |

`display_name_hi` values are plain spoken-Hindi glosses written by the team; have a Hindi speaker review them.
