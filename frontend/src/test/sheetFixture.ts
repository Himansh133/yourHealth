/** A doctor sheet as the API sends it (Decimals arrive as strings). */
export const SHEET = {
  profile: { display_name: "Papa", age: 58, sex: "male" },
  generated_on: "2026-10-29",
  date_from: "2026-05-01",
  date_to: "2026-10-29",
  include_medicines: true,
  flagged: [
    {
      test_name: "HbA1c", unit: "%", value: "7.2", flag: "high", observed_on: "2026-06-14", range_low: "4.0",
      range_high: "5.6", previous: { value: "8.1", observed_on: "2026-01-10" }, lab_result_id: "r2", document_id: "d2",
    },
  ],
  medicine_flags: [
    { medicine_name: "Glycomet 500", test_name: "Vitamin B12", message: "Metformin is known to lower Vitamin B12 over time.",
      source_url: "https://dailymed.nlm.nih.gov/x" },
  ],
  trends: [
    { test_name: "Creatinine", unit: "mg/dL", range_low: "0.7", range_high: "1.3",
      points: [{ value: "1.02", observed_on: "2026-05-10" }, { value: "1.05", observed_on: "2026-06-14" }] },
  ],
  medicines: [{ name: "Glycomet 500", generic: "metformin", dose_text: null, frequency: "twice a day", started_on: "2026-03-02" }],
  reports: [{ document_id: "d2", doc_type: "lab_report", title: "Dr Lal PathLabs", report_date: "2026-06-14" }],
};
