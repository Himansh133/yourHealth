import type { Doc, LabResult } from "../api/types";

export const ME = { id: "u1", email: "a@example.com", preferred_language: "en", account_type: "patient" };
export function report(over: Partial<Doc> = {}): Doc {
  return { id: "d2", profile_id: "p1", source_channel: "web", original_filename: "june.pdf", mime_type: "application/pdf",
    size_bytes: 100, doc_type: "lab_report", lab_name: "Demo lab", report_date: "2026-06-14", status: "done",
    error_code: null, created_at: "2026-06-15T10:00:00Z", ...over };
}
export function reading(over: Partial<LabResult> = {}): LabResult {
  return { id: "r2", document_id: "d2", test: { loinc_code: "4548-4", name: "HbA1c", name_hi: null, unit: "%", category: "Diabetes" },
    raw_name: "HbA1c", raw_value: "7.2", raw_unit: "%", raw_range: "4.0-5.6", printed_flag: null,
    value_num: 7.2, value_canonical: 7.2, qualifier: null, range_low: 4, range_high: 5.6, range_low_canonical: 4,
    range_high_canonical: 5.6, flag: "high", observed_on: "2026-06-14", page_no: 2, bbox: null,
    extraction_confidence: 0.95, verified_by_user: false, ...over };
}
