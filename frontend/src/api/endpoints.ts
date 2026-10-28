import { request } from "./client";
import type { Doc, LabResult, Profile, Sex, Trend, User } from "./types";

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
