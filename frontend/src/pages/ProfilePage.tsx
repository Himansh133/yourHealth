import { useEffect, useState, type ChangeEvent } from "react";
import { Link, NavLink, useParams } from "react-router-dom";
import { documents as documentsApi, profiles as profilesApi } from "../api/endpoints";
import type { Doc, DocumentStatus, Profile } from "../api/types";
import { ErrorAlert, errorMessage } from "../components/ui";
import { formatDate } from "../format";
import ChatPanel from "./ChatPanel";
import DoctorSheetPanel from "./DoctorSheetPanel";
import MedicinesPanel from "./MedicinesPanel";
import TrendsPanel from "./TrendsPanel";

const PENDING: DocumentStatus[] = ["queued", "extracting", "parsing", "indexing"];

const STATUS_LABEL: Record<DocumentStatus, string> = {
  queued: "Uploaded, waiting…",
  extracting: "Reading…",
  parsing: "Reading…",
  indexing: "Almost done…",
  needs_review: "Please check",
  done: "Done",
  failed: "Couldn't read this file",
};

const ERROR_HELP: Record<string, string> = {
  ocr_unavailable: "Photo reading is not available right now. Try a PDF, or upload again later.",
  processing_error: "Something went wrong while reading it. Try uploading again.",
};

export default function ProfilePage({ tab = "reports", pollMs = 2000 }: { tab?: "reports" | "trends" | "medicines" | "ask" | "sheet"; pollMs?: number }) {
  const { pid = "" } = useParams();
  const [profile, setProfile] = useState<Profile | null | undefined>(undefined);
  const [error, setError] = useState("");

  useEffect(() => {
    profilesApi
      .list()
      .then((all) => setProfile(all.find((p) => p.id === pid) ?? null))
      .catch((e) => setError(errorMessage(e)));
  }, [pid]);

  if (error) return <ErrorAlert>{error}</ErrorAlert>;
  if (profile === undefined) return <p className="text-slate-500">Loading…</p>;
  if (profile === null) return <p>Profile not found. <Link to="/" className="text-teal-700 underline">Back to family</Link></p>;

  const tabClass = ({ isActive }: { isActive: boolean }) =>
    `border-b-2 px-1 pb-2 font-medium ${isActive ? "border-teal-700 text-teal-800" : "border-transparent text-slate-500 hover:text-slate-800"}`;

  return (
    <div className="flex flex-col gap-6">
      <div className="print:hidden">
        <Link to="/" className="text-sm text-teal-700 hover:underline">← Family</Link>
        <h1 className="mt-1 text-2xl font-semibold">{profile.display_name}</h1>
      </div>
      <nav className="flex gap-6 overflow-x-auto border-b border-slate-200 print:hidden" aria-label="Profile sections">
        <NavLink to={`/profiles/${pid}`} end className={tabClass}>Reports</NavLink>
        <NavLink to={`/profiles/${pid}/trends`} className={tabClass}>Trends</NavLink>
        <NavLink to={`/profiles/${pid}/medicines`} className={tabClass}>Medicines</NavLink>
        <NavLink to={`/profiles/${pid}/ask`} className={tabClass}>Ask</NavLink>
        <NavLink to={`/profiles/${pid}/sheet`} className={tabClass}>Doctor sheet</NavLink>
      </nav>
      {tab === "reports" && <ReportsPanel profile={profile} pollMs={pollMs} />}
      {tab === "trends" && <TrendsPanel profileId={pid} />}
      {tab === "medicines" && <MedicinesPanel profileId={pid} canEdit={profile.role !== "viewer"} />}
      {tab === "ask" && <ChatPanel profileId={pid} profileName={profile.display_name} />}
      {tab === "sheet" && <DoctorSheetPanel profileId={pid} canShare={profile.role !== "viewer"} />}
    </div>
  );
}

function ReportsPanel({ profile, pollMs }: { profile: Profile; pollMs: number }) {
  const [docs, setDocs] = useState<Doc[] | null>(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const canEdit = profile.role !== "viewer";

  useEffect(() => {
    documentsApi.list(profile.id).then(setDocs).catch((e) => setError(errorMessage(e)));
  }, [profile.id]);

  // Poll only the documents still being processed; stop when none are.
  const pendingIds = (docs ?? []).filter((d) => PENDING.includes(d.status)).map((d) => d.id).join(",");
  useEffect(() => {
    if (!pendingIds) return;
    const timer = setTimeout(async () => {
      const fresh = await Promise.all(pendingIds.split(",").map((id) => documentsApi.get(id).catch(() => null)));
      setDocs((prev) => prev && prev.map((d) => fresh.find((f) => f?.id === d.id) ?? d));
    }, pollMs);
    return () => clearTimeout(timer);
  }, [pendingIds, pollMs, docs]);

  async function upload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError("");
    setUploading(true);
    try {
      const doc = await documentsApi.upload(profile.id, file);
      setDocs((prev) => [doc, ...(prev ?? []).filter((d) => d.id !== doc.id)]);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="flex flex-col gap-4">
      {canEdit && (
        <div>
          <label className="inline-flex cursor-pointer items-center rounded-md bg-teal-700 px-4 py-2 font-medium text-white hover:bg-teal-800 focus-within:ring-2 focus-within:ring-teal-600 focus-within:ring-offset-2">
            {uploading ? "Uploading…" : "Upload a report (PDF or photo)"}
            <input type="file" accept="application/pdf,image/jpeg,image/png" className="sr-only"
              disabled={uploading} onChange={upload} />
          </label>
          <p className="mt-1 text-xs text-slate-500">Up to 15 MB and 20 pages.</p>
        </div>
      )}
      <ErrorAlert>{error}</ErrorAlert>
      {docs === null && !error && <p className="text-slate-500">Loading…</p>}
      {docs?.length === 0 && <p className="text-slate-600">No reports yet for {profile.display_name}.</p>}
      <ul className="flex flex-col gap-2">
        {docs?.map((d) => <DocumentRow key={d.id} doc={d} />)}
      </ul>
    </section>
  );
}

function DocumentRow({ doc }: { doc: Doc }) {
  const title = doc.lab_name ?? doc.original_filename ?? "Report";
  const kind = { lab_report: "", prescription: "Prescription", discharge: "Discharge summary", other: "Other document", unknown: "" }[doc.doc_type];
  const tone =
    doc.status === "failed" ? "text-red-700" : doc.status === "needs_review" ? "text-amber-700" : doc.status === "done" ? "text-teal-700" : "text-slate-500";
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white p-4">
      <div>
        <p className="font-medium">{title}</p>
        <p className="text-sm text-slate-500">
          {[kind, doc.report_date ? formatDate(doc.report_date) : doc.status === "done" || doc.status === "needs_review" ? "Date not found" : ""]
            .filter(Boolean).join(" · ")}
        </p>
        {doc.status === "failed" && doc.error_code && (
          <p className="text-sm text-red-700">{ERROR_HELP[doc.error_code] ?? "Try uploading again."}</p>
        )}
      </div>
      <div className="flex items-center gap-4">
        <span className={`text-sm font-medium ${tone}`}>{STATUS_LABEL[doc.status]}</span>
        {doc.status === "needs_review" && (
          <Link to={`/documents/${doc.id}/review`} className="rounded-md bg-amber-600 px-3 py-1 text-sm font-medium text-white hover:bg-amber-700">
            Check values
          </Link>
        )}
        {doc.status === "done" && doc.doc_type === "lab_report" && (
          <Link to={`/documents/${doc.id}/review`} className="text-sm text-teal-700 hover:underline">View values</Link>
        )}
        {doc.status === "done" && doc.doc_type === "prescription" && (
          <Link to={`/profiles/${doc.profile_id}/medicines`} className="text-sm text-teal-700 hover:underline">Confirm medicines</Link>
        )}
      </div>
    </li>
  );
}
