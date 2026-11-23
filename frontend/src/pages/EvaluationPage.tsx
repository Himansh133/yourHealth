import data from "../data/evaluation.json";
import { formatDate } from "../format";

export default function EvaluationPage() {
  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm font-medium uppercase tracking-wide text-teal-800">Historical benchmark · Synthetic data</p>
        <h1 className="mt-2 text-2xl font-semibold">Evaluation &amp; evidence</h1>
        <p className="mt-2 max-w-3xl leading-relaxed text-slate-600">Compare the same model with three ways of answering report questions. These saved results document what was measured, including where the pipeline did not perform best.</p>
      </header>
      <dl className="grid gap-3 sm:grid-cols-3">
        {[['Test set', `${data.question_count} questions`], ['Run date', formatDate(data.run_date)], ['Code revision', data.code_revision]].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-200 bg-white p-4"><dt className="text-sm text-slate-600">{label}</dt><dd className="mt-1 text-xl font-semibold">{value}</dd></div>
        ))}
      </dl>
      <section className="rounded-lg border border-amber-200 bg-amber-50 p-4" aria-label="Evaluation limitations">
        <h2 className="font-semibold text-amber-950">Read these results in context</h2>
        <ul className="mt-2 list-disc space-y-2 pl-5 text-sm leading-relaxed text-amber-950">{data.limitations.map(t => <li key={t}>{t}</li>)}</ul>
      </section>
      <section className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <caption className="p-4 text-left text-slate-600">{data.dataset} · {data.model}. Counts in parentheses are successes / eligible questions unless a row states an error or fallback rate. “–” means not reported.</caption>
          <thead className="bg-slate-50"><tr><th scope="col" className="p-4">Metric</th>{data.systems.map(s => <th key={s} scope="col" className="p-4">{s}</th>)}</tr></thead>
          <tbody>{data.metrics.map(m => <tr key={m.label} className="border-t border-slate-100">
            <th scope="row" className="p-4 font-medium">{m.label}</th>
            {m.values.map((v, i) => <td key={i} className={`p-4 ${i === 2 ? "bg-teal-50 font-medium text-teal-950" : "text-slate-700"}`}>{v}</td>)}
          </tr>)}</tbody>
        </table>
      </section>
      <details className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
        <summary className="cursor-pointer py-1 font-medium text-teal-800">Dataset provenance &amp; reproducibility</summary>
        <p className="mt-3 text-slate-600">This page bundles aggregate metrics only. Source answer logs stay outside the frontend. Rebuild the artifact with <code>python -m eval.runners.export_dashboard</code> from the repository root.</p>
        <ul className="mt-3 space-y-3">{data.sources.map(s => <li key={s.path} className="break-all"><p className="font-medium">{s.path}</p><p className="mt-1 text-xs text-slate-600">SHA-256: {s.sha256}</p></li>)}</ul>
      </details>
    </div>
  );
}
