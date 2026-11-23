import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { documents, labs } from "../api/endpoints";
import type { Doc, LabResult } from "../api/types";
import { ErrorAlert, errorMessage } from "../components/ui";
import { formatDate } from "../format";
import { changeBetween, printedReading } from "./clinicalDisplay";

export default function OverviewPanel({ profileId, profileName }: { profileId: string; profileName: string }) {
  const [data, setData] = useState<{ pid: string; docs: Doc[]; rows: LabResult[] } | null>(null);
  const [error, setError] = useState<{ pid: string; text: string } | null>(null);
  useEffect(() => {
    let active = true;
    setError(null);
    Promise.all([documents.list(profileId), labs.list(profileId)]).then(([docs, rows]) => {
      if (active) setData({ pid: profileId, docs, rows });
    }).catch(e => { if (active) setError({ pid: profileId, text: errorMessage(e) }); });
    return () => { active = false; };
  }, [profileId]);
  if (error?.pid === profileId) return <ErrorAlert>{error.text}</ErrorAlert>;
  if (data?.pid !== profileId) return <p role="status" className="text-slate-600">Loading overview…</p>;
  const { docs, rows } = data;
  const grouped = new Map<string, LabResult[]>();
  for (const row of [...rows].sort((a, b) => b.observed_on.localeCompare(a.observed_on))) {
    const key = row.test?.loinc_code ?? `unmapped:${row.id}`;
    grouped.set(key, [...(grouped.get(key) ?? []), row]);
  }
  const latest = [...grouped.values()].flatMap(group => group.filter(r => r.observed_on === group[0].observed_on));
  const flagged = latest.filter(r => r.flag === "high" || r.flag === "low");
  const review = docs.filter(d => d.status === "needs_review");
  const latestDate = docs.map(d => d.report_date).filter((d): d is string => !!d).sort().at(-1);
  const changes = [...grouped.values()].flatMap(group => {
    const dates = [...new Set(group.map(r => r.observed_on))].slice(0, 2);
    if (dates.length < 2) return [];
    const current = group.filter(r => r.observed_on === dates[0]);
    const prior = group.filter(r => r.observed_on === dates[1]);
    if (current.length !== 1 || prior.length !== 1) return [];
    if (!docs.find(d => d.id === prior[0].document_id)?.report_date ||
        !docs.find(d => d.id === current[0].document_id)?.report_date) return [];
    const text = changeBetween(prior[0], current[0]);
    return text ? [{ before: prior[0], after: current[0], text }] : [];
  }).sort((a, b) => b.after.observed_on.localeCompare(a.after.observed_on)).slice(0, 3);
  return <section className="space-y-6">
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div><h2 className="text-xl font-semibold">At a glance</h2><p className="mt-1 text-sm text-slate-600">A summary of {profileName}'s saved reports. Values use each report's printed reference range.</p></div>
      <Link className="rounded-md bg-teal-700 px-4 py-2 font-medium text-white hover:bg-teal-800" to={`/profiles/${profileId}/reports`}>Upload a report</Link>
    </header>
    {docs.length === 0 ? <p className="rounded-lg border border-dashed border-slate-300 p-6 text-slate-600">No reports yet for {profileName}. Upload a PDF or photo to get started.</p> : <>
      <dl className="grid gap-3 sm:grid-cols-3">
        {[["Latest report date", latestDate ? formatDate(latestDate) : "Date not recorded"], ["Latest readings outside range", flagged.length], ["Reports to check", review.length]].map(([label, value]) => <div key={label} className="rounded-lg border border-slate-200 bg-white p-4"><dt className="text-sm text-slate-600">{label}</dt><dd className="mt-1 text-xl font-semibold">{value}</dd></div>)}
      </dl>
      {docs.some(d => ["queued", "extracting", "parsing", "indexing"].includes(d.status)) && <p role="status" className="text-sm text-slate-600">Some reports are still processing. Reopen this overview after they finish.</p>}
      {review.length > 0 && <section className="rounded-lg border border-amber-200 bg-amber-50 p-4"><h3 className="font-semibold">Check extracted values</h3><ul className="mt-2 space-y-2">{review.map(d => <li key={d.id}><Link className="inline-block py-1 text-amber-950 underline" to={`/documents/${d.id}/review`}>Review report · {d.report_date ? formatDate(d.report_date) : d.original_filename ?? "Undated report"}</Link></li>)}</ul></section>}
      <section className="rounded-lg border border-slate-200 bg-white p-4"><h3 className="font-semibold">Recent changes</h3>
        <p className="mt-1 text-sm text-slate-600">Two latest distinct dates per test, using comparable units. A rise or fall alone does not establish improvement.</p>
        {changes.length === 0 ? <p className="mt-3 text-sm text-slate-600">Not enough unambiguous, comparable results yet. Open reports to check dates and units.</p> : <ul className="mt-3 space-y-4">{changes.map(({ before, after, text }) => <li key={after.id}>
          <p className="font-medium">{after.test?.name} <span className="text-slate-600">· {text}</span></p>
          <p className="mt-1 text-sm text-slate-700"><Link className="text-teal-800 underline" to={`/documents/${before.document_id}/review`}>{before.value_canonical} {before.test?.unit} · {formatDate(before.observed_on)}</Link> → <Link className="text-teal-800 underline" to={`/documents/${after.document_id}/review`}>{after.value_canonical} {after.test?.unit} · {formatDate(after.observed_on)}</Link></p>
          <p className="mt-1 text-xs text-slate-600">{before.verified_by_user && after.verified_by_user ? "Both readings checked by you" : "Not checked yet"}</p>
        </li>)}</ul>}
      </section>
      <section className="rounded-lg border border-slate-200 bg-white p-4"><h3 className="font-semibold">Latest readings outside the printed range</h3>
        {flagged.length === 0 ? <p className="mt-3 text-sm text-slate-600">No latest saved readings flagged high or low. This is not an assessment of overall health.</p> : <ul className="mt-3 divide-y divide-slate-100">{flagged.map(r => <li key={r.id} className="flex flex-wrap items-start justify-between gap-2 py-3">
          <div><p className="font-medium">{r.test?.name ?? r.raw_name} · {printedReading(r)} · {r.flag === "high" ? "High" : "Low"}</p><p className="mt-1 text-sm text-slate-600">{formatDate(r.observed_on)} · {r.verified_by_user ? "Checked by you" : "Not checked yet"}</p></div>
          <Link className="py-1 text-sm text-teal-800 underline" to={`/documents/${r.document_id}/review`}>Open report{r.page_no ? `, page ${r.page_no}` : ""}</Link>
        </li>)}</ul>}
      </section>
    </>}
  </section>;
}
