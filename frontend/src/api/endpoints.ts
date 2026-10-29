import { request } from "./client";
import type { ChatAnswer, Doc, DrugSearchResult, Frequency, IngredientInfo, Insight, LabResult, Lang, Medicine, Profile, Sex, Share, ShareCreated, ShareExpiry, Sheet, Trend, User, WhatsAppLinkCode, WhatsAppStatus } from "./types";

export const auth = {
  me: () => request<User>("GET", "/me"),
  register: (email: string, password: string) => request<User>("POST", "/auth/register", { email, password }),
  login: (email: string, password: string) => request<User>("POST", "/auth/login", { email, password }),
  logout: () => request<void>("POST", "/auth/logout"),
};

export type ProfileInput = { display_name: string; birth_year?: number | null; sex?: Sex | null; relation_label?: string | null };

export const profiles = {
  list: () => request<Profile[]>("GET", "/profiles"),
  create: (body: ProfileInput) => request<Profile>("POST", "/profiles", body),
  update: (id: string, body: Partial<ProfileInput>) => request<Profile>("PATCH", `/profiles/${id}`, body),
  remove: (id: string) => request<void>("DELETE", `/profiles/${id}`),
};

export const documents = {
  list: (profileId: string) => request<Doc[]>("GET", `/profiles/${profileId}/documents`),
  get: (id: string) => request<Doc>("GET", `/documents/${id}`),
  upload: (profileId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Doc>("POST", `/profiles/${profileId}/documents`, form);
  },
  setReportDate: (id: string, report_date: string) => request<Doc>("PATCH", `/documents/${id}`, { report_date }),
  remove: (id: string) => request<void>("DELETE", `/documents/${id}`),
  fileUrl: (id: string) => `/api/v1/documents/${id}/file`,
};

export type LabResultPatch = Partial<Pick<LabResult, "raw_name" | "raw_value" | "raw_unit" | "raw_range">>;

export const labs = {
  forDocument: (profileId: string, documentId: string) =>
    request<LabResult[]>("GET", `/profiles/${profileId}/lab-results?document_id=${encodeURIComponent(documentId)}`),
  correct: (id: string, body: LabResultPatch) => request<LabResult>("PATCH", `/lab-results/${id}`, body),
  trends: (profileId: string) => request<Trend[]>("GET", `/profiles/${profileId}/trends`),
};

export type MedicineInput = {
  brand_id?: string;
  ingredient_id?: string;
  dose_text?: string;
  frequency_code?: Frequency;
  started_on?: string;
  stopped_on?: string;
};

export type MedicinePatch = Partial<Omit<MedicineInput, "ingredient_id">> & { confirmed_by_user?: true };

export const medicines = {
  search: (q: string) => request<DrugSearchResult[]>("GET", `/drugs/search?q=${encodeURIComponent(q)}`),
  ingredient: (id: string) => request<IngredientInfo>("GET", `/drugs/ingredients/${id}`),
  list: (profileId: string) => request<Medicine[]>("GET", `/profiles/${profileId}/medicines`),
  add: (profileId: string, body: MedicineInput) => request<Medicine>("POST", `/profiles/${profileId}/medicines`, body),
  update: (id: string, body: MedicinePatch) => request<Medicine>("PATCH", `/medicines/${id}`, body),
  remove: (id: string) => request<void>("DELETE", `/medicines/${id}`),
  insights: (profileId: string) => request<Insight[]>("GET", `/profiles/${profileId}/medicine-insights`),
};

export const chat = {
  ask: (profileId: string, question: string, lang: Lang) =>
    request<ChatAnswer>("POST", `/profiles/${profileId}/chat`, { question, lang }),
};

export type SheetQuery = { from: string; include_medicines: boolean };

export const sheets = {
  preview: (profileId: string, q: SheetQuery) =>
    request<Sheet>("GET", `/profiles/${profileId}/sheet?from=${q.from}&include_medicines=${q.include_medicines}`),
};

export const shares = {
  create: (profileId: string, body: SheetQuery & { expires_in: ShareExpiry }) =>
    request<ShareCreated>("POST", `/profiles/${profileId}/shares`, body),
  list: (profileId: string) => request<Share[]>("GET", `/profiles/${profileId}/shares`),
  revoke: (id: string) => request<void>("POST", `/shares/${id}/revoke`),
};

/** What a doctor uses: no account, just the link's token and the PIN. */
export const publicShare = {
  unlock: (token: string, pin: string) => request<{ ok: true }>("POST", `/s/${token}/unlock`, { pin }),
  sheet: (token: string) => request<Sheet>("GET", `/s/${token}/sheet`),
  documentUrl: (token: string, documentId: string) => `/api/v1/s/${token}/documents/${documentId}`,
};

export const whatsapp = {
  status: () => request<WhatsAppStatus>("GET", "/me/whatsapp"),
  linkCode: () => request<WhatsAppLinkCode>("POST", "/me/whatsapp/link-code"),
  unlink: () => request<void>("DELETE", "/me/whatsapp"),
};
