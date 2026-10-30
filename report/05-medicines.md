# 5. Medicines and their effect on lab values

The review panel's question was: *which medicine affects which value, and which medicine is good for it?* The app
answers the first part from official drug labels, shown as data and never as cause. It deliberately declines the
second part.

## 5.1 Getting a person's medicine list

- **Typed in:** the user types a brand or generic name and picks a match; the strength is part of the brand
  ("Glycomet 500").
- **From a printed prescription:** lines like `Tab Glycomet 500 1-0-1 x 30 days` are read for form, brand, strength,
  frequency (`1-0-1` → twice a day; OD, BD, TDS, QID, HS, SOS) and duration. Each line becomes an **unconfirmed**
  medicine. Nothing counts (in answers, insights or the doctor sheet) until the user confirms it, because a misread
  brand is a wrong medicine.

**Matching brands.** A brand name may have typos ("Glycomet" / "Glycomit"), but its strength must match exactly. An
earlier fuzzy match snapped "Telma 60" to Telma 40, which is a wrong dose. Brand names shorter than four letters
("Pan") are not matched inside chat questions, because they are everyday words.

Each brand maps to its ingredients (Telma H → telmisartan + hydrochlorothiazide). Everything after this point works at
ingredient level.

## 5.2 The medicine-to-lab effects table

`drug_lab_effects` has 32 hand-curated rows. Each row records:

| Field | Example |
|---|---|
| ingredient, test | metformin, HbA1c |
| direction | decrease |
| type | *therapeutic* (the intended effect) or *monitor* (worth checking) |
| typical onset | about 3 months |
| label section and evidence phrase | `indications_and_usage`, "glycemic control" |
| plain-language note | "Metformin is used to lower blood sugar. HbA1c reflects about the last 3 months, so changes show slowly." |

Examples of monitor rows: metformin can lower vitamin B12; hydrochlorothiazide can lower sodium and potassium;
telmisartan can raise potassium and creatinine. Every row was checked automatically against the label text it cites:
32 of 32 are supported (`refdata/EFFECTS_VERIFICATION.md`). A human pharmacology review is still pending.

## 5.3 "Is this medicine doing its job?" (insights)

For each confirmed medicine with a start date, and each test it is known to affect:

1. take the **last value before** the start date;
2. take the **latest value while on the medicine**, after the onset window (no HbA1c a week after starting metformin;
   nothing after the medicine was stopped);
3. compare the direction with the label's.

| Effect type | Moved the expected way | Didn't |
|---|---|---|
| therapeutic | "HbA1c went from 8.1% to 7.2% after metformin was started in Mar 2026. This matches the expected effect of metformin." | "… Worth discussing with your doctor." (flagged for the doctor sheet) |
| monitor | "Hydrochlorothiazide is known to lower sodium over time. Sodium went from 142 to 131 mmol/L. Worth mentioning to your doctor." (flagged) | stated as data, not flagged |

The plan originally compared with the *first* value after the onset window. In the browser check, a doctor sheet
flagged today's sodium of 131 in its table while the medicine card below quoted "142 → 140" from nine months earlier.
Using the latest value keeps the card and the table consistent (problem 7.7).

**What the app never says:** "this medicine caused it" or "this medicine isn't working, switch". Many things change lab
values: diet, other medicines, lab differences. The wording is tested against a list of causal and advice phrases.

## 5.4 On charts

Trend charts for a test draw a dashed line where a linked medicine was started (▸) or stopped (◂), labelled with the
ingredient, with the medicine's name and start date below the chart. The panel can see "HbA1c falling after
metformin" directly from SQL data, with no model involved.

## 5.5 "Which medicine is good for it?"

The app declines. Choosing a medicine depends on things it cannot see: other conditions, allergies, kidney function,
pregnancy, interactions. A treatment question ("Should I stop Glycomet?", "Which tablet for my sugar?") gets a fixed
reply: it says the choice is the doctor's, lists the person's own relevant values and current medicines with sources,
and offers to make a doctor visit sheet. The language model does not write this reply, so it cannot be argued into
giving advice. In the evaluation this reply was safe on 8 of 8 treatment questions; the plain-LLM and vector-RAG
baselines were safe on 2 of 8.
