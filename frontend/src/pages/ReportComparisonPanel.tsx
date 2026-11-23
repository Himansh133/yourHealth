import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { documents, labs } from "../api/endpoints";
import type { Doc, LabResult } from "../api/types";
import { ErrorAlert, errorMessage } from "../components/ui";
import { formatDate } from "../format";
import { changeBetween, printedReading } from "./clinicalDisplay";

export default function ReportComparisonPanel({ profileId }: { profileId: string }) {
  const [reports, setReports] = useState<{ pid: string; items: Doc[] } | null>(null);
  const [selection, setSelection] = useState({ pid: profileId, before: "", after: "" });
  const [results, setResults] = useState<{ key: string; before: LabResult[]; after: LabResult[] } | null>(null);
  const [error, setError] = useState<{ key: string; text: string } | null>(null);
  const before = selection.pid === profileId ? selection.before : "";
  const after = selection.pid === profileId ? selection.after : "";
  const requestKey = `${profileId}:${before}:${after}`;
  useEffect(() => {
    let active = true;
    setError(null);
    documents.list(profileId).then(docs => {
      if (!active) return;
      const items = docs.filter(d => d.doc_type === "lab_report" && ["done", "needs_review"].includes(d.status))
        .sort((a, b) => (a.report_date ?? "").localeCompare(b.report_date ?? "") || a.id.localeCompare(b.id));
      setReports({ pid: profileId, items });
      setSelection({ pid: profileId, before: items.at(-2)?.id ?? "", after: items.at(-1)?.id ?? "" });
    }).catch(e => { if (active) setError({ key: `docs:${profileId}`, text: errorMessage(e) }); });
    return () => { active = false; };
  }, [profileId]);
  useEffect(() => {
    if (!before || !after || before === after) return;
    let active = true;
    setError(null);
    Promise.all([labs.forDocument(profileId, before), labs.forDocument(profileId, after)]).then(([b, a]) => {
      if (active) setResults({ key: requestKey, before: b, after: a });
    }).catch(e => { if (active) setError({ key: requestKey, text: errorMessage(e) }); });
    return () => { active = false; };
  }, [profileId, before, after, requestKey]);
  if (error?.key === `docs:${profileId}`) return <ErrorAlert>{error.text}</ErrorAlert>;
  if (reports?.pid !== profileId) return <p role="status">Loading reports…</p>;
  if (reports.items.length < 2) return <section className="rounded-lg border border-dashed border-slate-300 p-6"><h2 className="text-xl font-semibold">Compare reports</h2><p className="mt-2 text-slate-600">Upload at least two processed lab reports to compare their readings.</p><Link className="mt-3 inline-block py-2 text-teal-800 underline" to={`/profiles/${profileId}/reports`}>Go to reports</Link></section>;
  const byTest = new Map<string, { name: string; before: LabResult[]; after: LabResult[] }>();
  if (results?.key === requestKey) {
    for (const side of ["before", "after"] as const) for (const row of results[side]) {
      const key = row.test?.loinc_code ?? `unmapped:${side}:${row.id}`;
      const group = byTest.get(key) ?? { name: row.test?.name ?? `${row.raw_name} (unmapped)`, before: [], after: [] };
      group[side].push(row);
      byTest.set(key, group);
    }
  }
  const bDoc = reports.items.find(d => d.id === before);
  const aDoc = reports.items.find(d => d.id === after);
  const datedPair = !!bDoc?.report_date && !!aDoc?.report_date && bDoc.report_date < aDoc.report_date;
  return <section className="space-y-4">
    <header><h2 className="text-xl font-semibold">Compare reports</h2><p className="mt-1 text-sm leading-relaxed text-slate-600">Printed readings side by side. Changes are absolute differences in normalized units; they do not establish a diagnosis or treatment effect.</p></header>
    <div className="grid gap-4 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2">
      {([['before', 'Earlier report'], ['after', 'Later report']] as const).map(([side, label]) => <label key={side} className="flex flex-col gap-2 text-sm font-medium">{label}
        <select className="min-w-0 rounded-md border border-slate-300 bg-white p-3 focus:ring-2 focus:ring-teal-600" value={side === "before" ? before : after} onChange={e => setSelection(s => ({ ...s, [side]: e.target.value }))}>
          {reports.items.map(d => <option key={d.id} value={d.id}>{d.report_date ? formatDate(d.report_date) : "Date not recorded"} · {d.lab_name ? `${d.lab_name} · ` : ""}{d.original_filename ?? d.id.slice(0, 8)}</option>)}
        </select>
      </label>)}
    </div>
    {before === after ? <p className="text-slate-600">Choose two different reports.</p> : <>
      {!datedPair && <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-950">Select a later report with a date after the earlier report. Numeric changes are hidden for missing, equal or reversed report dates.</p>}
      {error?.key === requestKey ? <ErrorAlert>{error.text}</ErrorAlert> : results?.key !== requestKey ? <p role="status">Loading readings…</p> : <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <caption className="p-4 text-left text-slate-600">{bDoc?.report_date ? formatDate(bDoc.report_date) : "Undated report"} → {aDoc?.report_date ? formatDate(aDoc.report_date) : "Undated report"}. Qualified values, unknown units and multiple readings are not compared.</caption>
          <thead className="bg-slate-50"><tr>{["Test", "Earlier reading", "Later reading", "Change in normalized units"].map(t => <th key={t} scope="col" className="p-4">{t}</th>)}</tr></thead>
          <tbody>{[...byTest].sort((a, b) => a[1].name.localeCompare(b[1].name)).map(([key, group]) => {
            const change = datedPair && group.before.length === 1 && group.after.length === 1 ? changeBetween(group.before[0], group.after[0]) : null;
            return <tr key={key} className="border-t border-slate-100 align-top"><th scope="row" className="p-4 font-medium">{group.name}</th><td className="p-4"><ReadingCell rows={group.before} /></td><td className="p-4"><ReadingCell rows={group.after} /></td><td className="p-4 font-medium">{change ?? "Not comparable"}</td></tr>;
          })}</tbody>
        </table>
        {byTest.size === 0 && <p className="p-4 text-slate-600">No extracted lab readings in these reports. Open the reports to check their contents.</p>}
      </div>}
    </>}
  </section>;
}

function ReadingCell({ rows }: { rows: LabResult[] }) {
  if (!rows.length) return <span className="text-slate-600">Not in this report</span>;
  return <div className="space-y-3">
    {rows.length > 1 && <p className="font-medium text-amber-950">Multiple readings; review the report</p>}
    {rows.map(r => <div key={r.id}>
      <Link className="inline-block py-1 text-teal-800 underline" to={`/documents/${r.document_id}/review`}>{printedReading(r)}{r.page_no ? ` · page ${r.page_no}` : ""}</Link>
      <p className="mt-1 text-slate-600">{formatDate(r.observed_on)} · {r.flag === "high" ? "High" : r.flag === "low" ? "Low" : r.flag === "normal" ? "Within printed range" : "No numeric range assessment"}</p>
      {r.raw_range && <p className="mt-1 text-xs text-slate-600">Printed range: {r.raw_range}</p>}
      <p className="mt-1 text-xs text-slate-600">{r.verified_by_user ? "Checked by you" : "Not checked yet"}</p>
    </div>)}
  </div>;
}
