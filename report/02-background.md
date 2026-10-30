# 2. Background and data sources

## 2.1 Existing services

> **Check before submitting:** the descriptions of other products below are from the project plan, not from a fresh
> review. Confirm each against the product's current website and cite it.

India already has digital health record services: ABHA (the Ayushman Bharat Health Account) and the ABDM network
for linking records, DigiLocker for storing documents, and consumer apps such as Eka Care. They are built mainly to
**store and move** records. YourHealth targets a narrower job: turning the reports a family already has, often as
WhatsApp images, into per-test trends, linking them to the medicines the person takes, and explaining them in Hindi.
It also publishes measured accuracy, which consumer apps generally don't. Integration with ABHA / ABDM is future work
(Section 9).

## 2.2 Retrieval-augmented generation and its limits here

Retrieval-augmented generation (RAG) gives a language model passages retrieved from a document collection and asks it
to answer from them. A plain vector-RAG system embeds the question, finds the nearest passages and passes them to the
model. For lab reports this fails in predictable ways:

- **"Latest value" questions**: many reports contain the same test, and the nearest passage is not necessarily the most
  recent one.
- **Trends** need every value in date order, which top-k retrieval does not return.
- **Medicine questions** need knowledge that isn't in the reports at all (what a brand contains, what it is used for).
- **Safety**: the model may answer "should I stop this medicine?" from general knowledge.

YourHealth therefore routes each question: structured questions go to SQL and to a curated medicine tool, and only
questions about what a document says go to retrieval. Section 8 compares this against plain-LLM and vector-RAG
baselines.

## 2.3 Reference data

All reference data is loaded once, offline. No patient data is ever sent to these sources.

| Data | Source | Use |
|---|---|---|
| Lab test codes and names (18 tests) | LOINC codes, team-written aliases (68) and Hindi glosses | Canonical identity of each test; matching printed names |
| Unit conversions (11) | Molar masses; IFCC↔NGSP formula for HbA1c | Putting values from different labs in one unit |
| Medicines: 23 ingredients, 41 common Indian brands | Typed by the team from pack compositions | Brand → ingredient, e.g. Glycomet 500 → metformin |
| Indian → US generic names | Team table (e.g. paracetamol → acetaminophen) | Joining Indian brands to US labels |
| Drug label text | openFDA Drug Label API (public domain), one label per ingredient | What a medicine is used for; source of every medicine-to-lab effect |
| Medicine-to-lab effects (32 rows) | Curated by the team; every row cites a label section and an evidence phrase | "Metformin lowers HbA1c", "hydrochlorothiazide can lower sodium" |

**Why US labels for an Indian app?** India has no free, structured drug-label API. Ingredients are the same molecules
everywhere, so the app maps an Indian brand to its ingredient using Indian data, then uses ingredient-level label
information. Vildagliptin has no US label and cholecalciferol has no single-ingredient label; these gaps are recorded
in `refdata/SOURCES.md`.

**Verification status.** All 32 effect rows are supported by the label text they cite
(`refdata/EFFECTS_VERIFICATION.md`). LOINC codes, brand compositions and the Hindi glosses still need an external check
by a faculty mentor or pharmacist, and a native Hindi speaker.

## 2.4 Deliberately not used

- Scraping online pharmacies: it breaks their terms of service.
- The language model's own medical knowledge as a source of facts.
- Real patient reports during development: all development and evaluation use synthetic patients (Section 8).
