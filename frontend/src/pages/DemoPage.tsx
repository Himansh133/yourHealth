import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { documents, profiles } from "../api/endpoints";
import { Button, ErrorAlert, errorMessage } from "../components/ui";

const REPORTS = ["sample-2026-01-10.pdf", "sample-2026-03-12.pdf", "sample-2026-06-14.pdf"];
const STEPS = [
  ["1", "Review", "Open a report and check extracted values against the PDF."],
  ["2", "Compare", "Compare January with June. HbA1c falls from 8.1% to 7.2%."],
  ["3", "Ask", "Ask for recent report trends, then expand the evidence panel."],
  ["4", "Challenge", "Ask for a test that is absent. Check that the app says it cannot find it."],
];

export default function DemoPage() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const [createdId, setCreatedId] = useState<string | null>(null);
  async function create() {
    setBusy(true);
    setError("");
    try {
      setProgress("Loading the three sample reports…");
      const files = await Promise.all(REPORTS.map(async name => {
        const response = await fetch(`/demo/${name}`);
        if (!response.ok || !response.headers.get("content-type")?.includes("application/pdf")) throw new Error("Could not load sample reports. Try again.");
        return new File([await response.blob()], name, { type: "application/pdf" });
      }));
      let pid = createdId;
      if (!pid) {
        setProgress("Creating a separate synthetic patient…");
        const profile = await profiles.create({ display_name: "Demo · Sample Patient", relation_label: "Synthetic demo data" });
        pid = profile.id;
        setCreatedId(pid);
      }
      for (const [i, file] of files.entries()) {
        setProgress(`Uploading sample report ${i + 1} of 3…`);
        await documents.upload(pid, file);
      }
      navigate(`/profiles/${pid}/reports`);
    } catch (e) { setError(errorMessage(e)); setProgress(""); }
    finally { setBusy(false); }
  }
  return <div className="space-y-6">
    <header><p className="text-sm font-medium uppercase tracking-wide text-teal-800">Presentation workspace</p><h1 className="mt-2 text-2xl font-semibold">Try a complete report journey</h1><p className="mt-2 max-w-2xl leading-relaxed text-slate-600">Three fictional lab reports, one clearly labelled patient, and a repeatable way to demonstrate the app. No real patient information is included.</p></header>
    <section className="rounded-lg border border-teal-200 bg-teal-50 p-5">
      <h2 className="text-lg font-semibold text-teal-950">Synthetic demo data</h2>
      <p className="mt-2 text-sm leading-relaxed text-teal-950">Creates a new profile in your account and uploads the January, March and June reports through the normal processing pipeline. It does not add data to an existing family member. The document worker must be running; report questions also need a configured model for generated summaries.</p>
      <Button className="mt-4 min-h-11" type="button" disabled={busy} onClick={() => void create()}>{busy ? "Preparing demo…" : createdId ? "Retry demo setup" : "Create demo patient"}</Button>
      {busy && <p role="status" className="mt-3 text-sm text-teal-950">{progress}</p>}
      <div className="mt-3"><ErrorAlert>{error}</ErrorAlert></div>
      {createdId && error && <p className="mt-2 text-sm">A demo profile was created. Retry to finish the uploads, or <Link className="text-teal-800 underline" to={`/profiles/${createdId}/reports`}>open its reports</Link>. Previously uploaded files are deduplicated.</p>}
    </section>
    <div className="grid gap-3 sm:grid-cols-2">{STEPS.map(([number, title, text]) => <section key={number} className="rounded-lg border border-slate-200 bg-white p-5"><p className="text-sm font-medium text-teal-800">Step {number}</p><h2 className="mt-1 font-semibold">{title}</h2><p className="mt-2 text-sm leading-relaxed text-slate-600">{text}</p></section>)}</div>
    <section className="rounded-lg border border-slate-200 bg-white p-5"><h2 className="font-semibold">Sample questions</h2><ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700"><li>Tell me the recent trends of my reports.</li><li>What was my latest HbA1c?</li><li>What was my vitamin D result? <span className="text-slate-600">(Not present in the sample reports.)</span></li></ul></section>
    <section className="rounded-lg border border-slate-200 bg-white p-5"><h2 className="font-semibold">Prefer to upload the samples yourself?</h2><ul className="mt-2 space-y-2">{REPORTS.map(name => <li key={name}><a className="inline-block py-2 text-sm text-teal-800 underline" href={`/demo/${name}`} download>{name}</a></li>)}</ul></section>
    <Link className="inline-block py-2 font-medium text-teal-800 underline" to="/evaluation">Explore the historical evaluation and its limitations →</Link>
  </div>;
}
