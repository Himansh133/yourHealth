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

export type Trend = { test: LabTest; points: TrendPoint[]; latest: TrendPoint; markers: MedicineMarker[] };

export type Frequency = "OD" | "BD" | "TDS" | "QID" | "HS" | "SOS";

export type Ingredient = { id: string; name: string; drug_class: string | null; used_for: string | null };

export type DrugSearchResult = {
  kind: "brand" | "ingredient";
  id: string;
  name: string;
  composition: string | null;
  ingredients: Ingredient[];
  drug_class: string | null;
};

export type LabEffect = {
  test: LabTest;
  direction: "increase" | "decrease" | "either";
  effect_type: "therapeutic" | "monitor";
  typical_onset: string | null;
  note_en: string;
  source_name: string;
  source_section: string;
  source_url: string;
  reviewed_by: string | null;
};

export type IngredientInfo = Ingredient & { atc_code: string | null; label_url: string | null; effects: LabEffect[] };

export type Medicine = {
  id: string;
  name: string;
  brand_id: string | null;
  composition: string | null;
  ingredients: Ingredient[];
  raw_text: string;
  dose_text: string | null;
  frequency_code: Frequency | null;
  started_on: string | null;
  stopped_on: string | null;
  confirmed_by_user: boolean;
  source_document_id: string | null;
};

export type Insight = {
  medicine_id: string;
  medicine_name: string;
  ingredient: string;
  test_name: string;
  status: "matches_expected" | "not_as_expected" | "watch" | "no_change_seen" | "not_enough_data" | "no_start_date";
  flagged: boolean;
  message: string;
  source_url: string;
  source_section: string;
};

export type MedicineMarker = {
  date: string;
  kind: "start" | "stop";
  medicine: string;
  ingredient: string;
  effect_type: "therapeutic" | "monitor";
};

export type ChatSource =
  | { id: string; kind: "lab_result"; lab_result_id: string; document_id: string; page_no?: number }
  | { id: string; kind: "document"; document_id: string; page_no?: number }
  | { id: string; kind: "medicine"; medicine_id: string }
  | { id: string; kind: "drug_label"; url?: string };

export type ChatAnswer = {
  answerable: boolean;
  summary: string;
  claims: { text: string; evidence_ids: string[] }[];
  missing_info: string[];
  doctor_note: string;
  fallback: boolean; // the LLM answer failed checks, so these are the values straight from the reports
  route: string[];
  sources: ChatSource[];
};

export type Lang = "en" | "hi";

/** Doctor visit sheet (plan 13.1). Decimal values arrive as strings. */
export type SheetReading = { value: string; observed_on: string };

export type Sheet = {
  profile: { display_name: string; age: number | null; sex: string | null };
  generated_on: string;
  date_from: string;
  date_to: string;
  include_medicines: boolean;
  flagged: {
    test_name: string; unit: string; value: string; flag: "low" | "high"; observed_on: string;
    range_low: string | null; range_high: string | null; previous: SheetReading | null;
    lab_result_id: string; document_id: string;
  }[];
  medicine_flags: { medicine_name: string; test_name: string; message: string; source_url: string }[];
  trends: { test_name: string; unit: string; range_low: string | null; range_high: string | null; points: SheetReading[] }[];
  medicines: { name: string; generic: string; dose_text: string | null; frequency: string | null; started_on: string | null }[];
  reports: { document_id: string; doc_type: string; title: string | null; report_date: string }[];
};

export type ShareExpiry = "1h" | "24h" | "7d";

export type ShareCreated = { share_id: string; url: string; pin: string; qr_png_base64: string; expires_at: string };

export type Share = {
  id: string;
  created_at: string;
  expires_at: string;
  state: "active" | "expired" | "revoked" | "locked";
  scope: { from: string; to: string; include_medicines: boolean };
  opens: number;
  last_opened_at: string | null;
};

export type WhatsAppStatus = { linked: boolean; phone: string | null; linked_at: string | null };
export type WhatsAppLinkCode = { code: string; expires_at: string; bot_number: string };
