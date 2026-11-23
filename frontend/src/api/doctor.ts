import { request } from './client';
import type { ChatAnswer, Medicine, Sheet } from './types';

export type Scope = { allergies: boolean; medicines: boolean; labs: boolean; documents: boolean; excluded_document_ids: string[] };
export const defaultScope = (): Scope => ({ allergies: true, medicines: true, labs: true, documents: true, excluded_document_ids: [] });
export type DoctorIdentity = { user_id: string; full_name: string; registration_number: string; registration_council: string };
export type Grant = { id: string; profile_id: string; display_name: string; expires_at: string; created_via: string };
export type PatientGrant = Grant & { doctor: DoctorIdentity; scope: Scope; revoked_at: string | null; last_used_at: string | null };
export type AccessRequest = { id: string; profile_id: string; display_name: string; doctor: DoctorIdentity; reason_text: string | null; requested_hours: number; status: string; expires_at: string };
export type ClinicCode = { code: string; patient_code: string; expires_at: string; qr_png_base64: string };
export type AccessEvent = { id: number; at: string; action: string; doctor_name: string | null; outcome: string };
export type AllergyStatus = 'unknown' | 'has_allergies' | 'none_known_confirmed';
export type Allergy = { id: string; substance_text: string; ingredient_id: string | null; drug_class: string | null; reaction_text: string | null; severity: 'unknown' | 'mild' | 'moderate' | 'severe'; source: 'patient' | 'document'; source_document_id: string | null; page_no: number | null; confirmed_by_user: boolean; is_absence: boolean };
export type Allergies = { status: AllergyStatus; confirmed_at: string | null; entries: Allergy[] };
export type AllergyInput = Pick<Allergy, 'substance_text' | 'reaction_text' | 'severity'> & Partial<Pick<Allergy, 'ingredient_id' | 'drug_class'>>;
export const access = {
  requests: () => request<AccessRequest[]>('GET', '/me/access-requests'),
  grants: (pid: string) => request<PatientGrant[]>('GET', `/profiles/${pid}/access-grants`),
  history: (pid: string) => request<AccessEvent[]>('GET', `/profiles/${pid}/access-history`),
  approve: (id: string, hours: number, scope: Scope) => request<PatientGrant>('POST', `/access-requests/${id}/approve`, { hours, scope }),
  deny: (id: string) => request('POST', `/access-requests/${id}/deny`),
  revoke: (id: string) => request('POST', `/access-grants/${id}/revoke`),
  clinic: (pid: string, hours: number, scope: Scope) => request<ClinicCode>('POST', `/profiles/${pid}/clinic-code`, { hours, scope }),
};
export const allergies = {
  list: (pid: string) => request<Allergies>('GET', `/profiles/${pid}/allergies`),
  add: (pid: string, body: AllergyInput) => request<Allergy>('POST', `/profiles/${pid}/allergies`, body),
  update: (pid: string, id: string, body: Partial<AllergyInput> & { confirmed_by_user?: boolean }) => request<Allergy>('PATCH', `/profiles/${pid}/allergies/${id}`, body),
  remove: (pid: string, id: string) => request('DELETE', `/profiles/${pid}/allergies/${id}`),
  status: (pid: string, status: AllergyStatus) => request('PUT', `/profiles/${pid}/allergy-status`, { status }),
};
export const doctorAccess = {
  lookup: (patient_code: string, reason: string, hours: number) => request<{ message: string }>('POST', '/doctor/lookup', { patient_code, reason, hours }),
  grants: () => request<Grant[]>('GET', '/doctor/grants'),
  redeem: (patient_code: string, code: string) => request<Grant>('POST', '/doctor/clinic-code/redeem', { patient_code, code }),
};
export type DoctorChatAnswer = Omit<ChatAnswer, 'sources'> & { sources: Array<{ id: string; kind: string; document_id?: string; page_no?: number; url?: string; allergy_id?: string }> };
export type Snapshot = {
  profile: { id: string; display_name: string; age: number | null; sex: string | null };
  grant: { id: string; expires_at: string };
  allergies: (Allergies & { message: string }) | null;
  current_medicines: Medicine[] | null; past_medicines: Medicine[] | null;
  flagged_labs: Array<Sheet['flagged'][number] & { verified_by_user: boolean; page_no: number | null }> | null;
  medicine_flags: Array<{ message: string; source_url: string; medicine_name: string; test_name: string }> | null;
  reports: Array<{ id: string; original_filename: string | null; lab_name: string | null; report_date: string | null; doc_type: string }> | null;
  footer: string;
};
export type MedicineCheck = { medicine_text: string; resolved: boolean; ingredients: Array<{ id: string; name: string }>; allergy_status: string;
  warnings: Array<{ kind: string; message: string; sources: Array<{ kind: string; id?: string; document_id?: string; page_no?: number; url?: string; section?: string }> }>;
  message: string; checks: Record<string, 'checked' | 'unavailable'> };
export type ChatMessage = { question: string; answer: DoctorChatAnswer };
export const clinical = {
  snapshot: (pid: string) => request<Snapshot>('GET', `/doctor/patients/${pid}/snapshot`),
  file: (pid: string, did: string, page = 1) => `/api/v1/doctor/patients/${pid}/documents/${did}#page=${page}`,
  chat: (pid: string, question: string) => request<DoctorChatAnswer>('POST', `/doctor/patients/${pid}/chat`, { question }),
  history: (pid: string) => request<{ messages: ChatMessage[] }>('GET', `/doctor/patients/${pid}/chat`),
  check: (pid: string, medicine_text: string) => request<MedicineCheck>('POST', `/doctor/patients/${pid}/medicine-check`, { medicine_text }),
};
