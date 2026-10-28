import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { documents as documentsApi, labs, type LabResultPatch } from "../api/endpoints";
import type { Doc, Flag, LabResult } from "../api/types";
import { Button, ErrorAlert, errorMessage } from "../components/ui";
import { formatDate } from "../format";

const REVIEW_BELOW = 0.6; // same threshold as the backend

const FLAG_LABEL: Record<Flag, string> = {
  high: "High",
  low: "Low",
  normal: "Normal",
  no_range: "No range printed",
  non_numeric: "—",
};

function doubtful(r: LabResult) {
  return !r.verified_by_user && (r.extraction_confidence ?? 0) < REVIEW_BELOW;
}

export default function ReviewPage() {
  const { did = "" } = useParams();
  const [doc, setDoc] = useState<Doc | null>(null);
  const [rows, setRows] = useState<LabResult[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    documentsApi
      .get(did)
      .then(async (d) => {
        setDoc(d);
        setRows(await labs.forDocument(d.profile_id, d.id));
      })
      .catch((e) => setError(e?.status === 404 ? "Report not found." : errorMessage(e)));
  }, [did]);

  async function refreshDoc() {
    setDoc(await documentsApi.get(did));
  }

  async function saveRow(id: string, patch: LabResultPatch) {
    const updated = await labs.correct(id, patch);
    setRows((prev) => prev && prev.map((r) => (r.id === id ? updated : r)));
    await refreshDoc();
  }

  if (error) return <ErrorAlert>{error}</ErrorAlert>;
  if (!doc || !rows) return <p className="text-slate-500">Loading…</p>;

  const fileUrl = documentsApi.fileUrl(doc.id);
  const toCheck = rows.filter(doubtful).length;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Link to={`/profiles/${doc.profile_id}`} className="text-sm text-teal-700 hover:underline">← Reports</Link>
        <h1 className="mt-1 text-2xl font-semibold">{doc.lab_name ?? doc.original_filename ?? "Report"}</h1>
        <p className="text-slate-600">
          {doc.report_date ? formatDate(doc.report_date) : "Date not found"}
          {toCheck > 0 && ` · ${toCheck} value${toCheck > 1 ? "s" : ""} to check`}
        </p>
      </div>

      {doc.status === "done" && (
        <p className="rounded-md border border-teal-200 bg-teal-50 px-3 py-2 text-teal-900">All values checked. They now appear in trends.</p>
      )}
      {!doc.report_date && doc.doc_type === "lab_report" && <ReportDateForm doc={doc} onSaved={setDoc} />}

      <div className="grid gap-4 lg:grid-cols-2">
        <section aria-label="Original report" className="min-h-[24rem] overflow-hidden rounded-lg border border-slate-200 bg-white">
          {doc.mime_type === "application/pdf" ? (
            <iframe title="Original report" src={fileUrl} className="h-[70vh] w-full" />
          ) : (
            <img alt="Original report" src={fileUrl} className="w-full" />
          )}
        </section>
        <section aria-label="Extracted values" className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th className="px-3 py-2 font-medium">Test</th>
                <th className="px-3 py-2 font-medium">Value</th>
                <th className="px-3 py-2 font-medium">Range</th>
                <th className="px-3 py-2 font-medium">Flag</th>
                <th className="px-3 py-2 font-medium"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => <ResultRow key={r.id} row={r} onSave={(p) => saveRow(r.id, p)} />)}
            </tbody>
          </table>
          {rows.length === 0 && <p className="p-4 text-slate-600">No test values were found in this file.</p>}
        </section>
      </div>
    </div>
  );
}

function ResultRow({ row, onSave }: { row: LabResult; onSave: (p: LabResultPatch) => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const check = doubtful(row);

  async function save(patch: LabResultPatch) {
    setError("");
    try {
      await onSave(patch);
      setEditing(false);
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  if (editing) return <EditRow row={row} error={error} onCancel={() => setEditing(false)} onSave={save} />;

  return (
    <tr className={`border-t border-slate-100 ${check ? "bg-amber-50" : ""}`}>
      <td className="px-3 py-2">
        <span className="font-medium">{row.raw_name}</span>
        {row.test && row.test.name !== row.raw_name && <span className="block text-xs text-slate-500">{row.test.name}</span>}
        {!row.test && <span className="block text-xs text-slate-500">Not in our test list</span>}
      </td>
      <td className="px-3 py-2"><span>{row.raw_value}</span> <span className="text-slate-500">{row.raw_unit}</span></td>
      <td className="px-3 py-2 text-slate-600">{row.raw_range ?? "—"}</td>
      <td className={`px-3 py-2 ${row.flag === "high" || row.flag === "low" ? "font-medium text-red-700" : "text-slate-600"}`}>
        {FLAG_LABEL[row.flag]}
      </td>
      <td className="px-3 py-2 text-right">
        <div className="flex flex-wrap items-center justify-end gap-2">
          {check && <span className="text-xs font-medium text-amber-800">Please check</span>}
          {row.verified_by_user && <span className="text-xs font-medium text-teal-700">Checked ✓</span>}
          {check && <Button variant="secondary" className="!px-2 !py-1 text-xs" onClick={() => save({})}>Looks right</Button>}
          <Button variant="link" className="text-xs" aria-label={`Edit ${row.raw_name}`} onClick={() => setEditing(true)}>Edit</Button>
        </div>
        {error && <ErrorAlert>{error}</ErrorAlert>}
      </td>
    </tr>
  );
}

function EditRow({ row, error, onCancel, onSave }: {
  row: LabResult; error: string; onCancel: () => void; onSave: (p: LabResultPatch) => Promise<void>;
}) {
  const [values, setValues] = useState({
    raw_name: row.raw_name, raw_value: row.raw_value, raw_unit: row.raw_unit ?? "", raw_range: row.raw_range ?? "",
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    // Send only what changed, so the backend knows which part was corrected.
    const patch: LabResultPatch = {};
    if (values.raw_name !== row.raw_name) patch.raw_name = values.raw_name;
    if (values.raw_value !== row.raw_value) patch.raw_value = values.raw_value;
    if (values.raw_unit !== (row.raw_unit ?? "")) patch.raw_unit = values.raw_unit;
    if (values.raw_range !== (row.raw_range ?? "")) patch.raw_range = values.raw_range;
    void onSave(patch);
  }

  const field = (key: keyof typeof values, label: string, width: string) => (
    <label className="flex flex-col text-xs text-slate-600">
      {label}
      <input value={values[key]} onChange={(e) => setValues({ ...values, [key]: e.target.value })}
        className={`${width} rounded border border-slate-300 px-2 py-1 text-sm text-slate-900`} />
    </label>
  );

  return (
    <tr className="border-t border-slate-100 bg-slate-50">
      <td colSpan={5} className="px-3 py-3">
        <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
          {field("raw_name", "Test name", "w-48")}
          {field("raw_value", "Value", "w-20")}
          {field("raw_unit", "Unit", "w-24")}
          {field("raw_range", "Range", "w-28")}
          <Button type="submit" className="!px-3 !py-1 text-sm">Save</Button>
          <Button type="button" variant="secondary" className="!px-3 !py-1 text-sm" onClick={onCancel}>Cancel</Button>
        </form>
        <ErrorAlert>{error}</ErrorAlert>
      </td>
    </tr>
  );
}

function ReportDateForm({ doc, onSaved }: { doc: Doc; onSaved: (d: Doc) => void }) {
  const [value, setValue] = useState("");
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      onSaved(await documentsApi.setReportDate(doc.id, value));
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-wrap items-end gap-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-3">
      <p className="w-full text-amber-900">The report date wasn't found. Enter the sample collection date from the report:</p>
      <label className="flex flex-col text-sm text-slate-700">
        Report date
        <input type="date" required value={value} max={new Date().toISOString().slice(0, 10)}
          onChange={(e) => setValue(e.target.value)} className="rounded border border-slate-300 px-2 py-1" />
      </label>
      <Button type="submit" className="!px-3 !py-1 text-sm">Save date</Button>
      <ErrorAlert>{error}</ErrorAlert>
    </form>
  );
}
