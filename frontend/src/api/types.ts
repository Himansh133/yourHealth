// Mirrors the FastAPI response models in backend/app/api/routes. Keep in sync.

export type User = { id: string; email: string; preferred_language: string };

export type Sex = "male" | "female" | "other" | "unknown";
export type Role = "owner" | "caregiver" | "viewer";

export type Profile = {
  id: string;
  display_name: string;
  birth_year: number | null;
  sex: Sex | null;
  role: Role;
  relation_label: string | null;
};

export type DocumentStatus = "queued" | "extracting" | "parsing" | "indexing" | "needs_review" | "done" | "failed";

export type Doc = {
  id: string;
  profile_id: string;
  source_channel: "web" | "whatsapp";
  original_filename: string | null;
  mime_type: string;
  size_bytes: number;
  doc_type: "lab_report" | "prescription" | "discharge" | "other" | "unknown";
  lab_name: string | null;
  report_date: string | null;
  status: DocumentStatus;
  error_code: string | null;
  created_at: string;
};

export type LabTest = { loinc_code: string; name: string; name_hi: string | null; unit: string; category: string | null };

export type Flag = "low" | "high" | "normal" | "no_range" | "non_numeric";

export type LabResult = {
  id: string;
  document_id: string;
  test: LabTest | null;
  raw_name: string;
  raw_value: string;
  raw_unit: string | null;
  raw_range: string | null;
  printed_flag: string | null;
  value_num: number | null;
  value_canonical: number | null;
  qualifier: string | null;
  range_low: number | null;
  range_high: number | null;
  range_low_canonical: number | null;
  range_high_canonical: number | null;
  flag: Flag;
  observed_on: string;
  page_no: number | null;
  bbox: { x0: number; y0: number; x1: number; y1: number } | null;
  extraction_confidence: number | null;
  verified_by_user: boolean;
};

export type TrendPoint = {
  lab_result_id: string;
  document_id: string;
  page_no: number | null;
  observed_on: string;
  value: number;
  qualifier: string | null;
  range_low: number | null;
  range_high: number | null;
  flag: Flag;
  low_confidence: boolean;
};

export type Trend = { test: LabTest; points: TrendPoint[]; latest: TrendPoint };
