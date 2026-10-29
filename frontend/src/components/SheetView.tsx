import type { ReactNode } from "react";
import type { Sheet } from "../api/types";
import { formatDate } from "../format";

const DOC_TYPE: Record<string, string> = { lab_report: "Lab report", prescription: "Prescription", discharge: "Discharge summary" };

/** The doctor visit sheet (plan 13.1), shown in the app and on the doctor's share page. Prints cleanly. */
export default function SheetView({ sheet, documentHref }: { sheet: Sheet; documentHref: (id: string) => string }) {
  const { profile } = sheet;
  return (
    <article className="flex flex-col gap-6 rounded-lg border border-slate-200 bg-white p-6 print:border-0 print:p-0">
      <header>
        <h2 className="text-xl font-semibold">{profile.display_name}</h2>
        <p className="text-sm text-slate-600">
          {[profile.age !== null ? `${profile.age} years` : null, profile.sex].filter(Boolean).join(" · ")}
        </p>
        <p className="text-sm text-slate-600">
          Reports from {formatDate(sheet.date_from)} to {formatDate(sheet.date_to)} · made on {formatDate(sheet.generated_on)}
        </p>
      </header>

      <Section title="Values outside the report's range" empty={sheet.flagged.length === 0 && "None in this period."}>
        <table className="w-full text-left text-sm">
          <thead className="text-slate-500">
            <tr><th className="py-1 pr-4 font-medium">Test</th><th className="pr-4 font-medium">Latest</th>
              <th className="pr-4 font-medium">Report's range</th><th className="font-medium">Before that</th></tr>
          </thead>
          <tbody>
            {sheet.flagged.map((f) => (
              <tr key={f.lab_result_id} className="border-t border-slate-100">
                <td className="py-1 pr-4 font-medium">{f.test_name}</td>
                <td className="pr-4">
                  <span>{f.value} {f.unit}</span>{" "}
                  <span className={f.flag === "high" ? "text-red-700" : "text-amber-700"}>{f.flag === "high" ? "High" : "Low"}</span>
                  <span className="block text-xs text-slate-500">{formatDate(f.observed_on)}</span>
                </td>
                <td className="pr-4">{range(f.range_low, f.range_high, f.unit)}</td>
                <td>{f.previous ? `${f.previous.value} ${f.unit} on ${formatDate(f.previous.observed_on)}` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      {sheet.include_medicines && sheet.medicine_flags.length > 0 && (
        <Section title="Worth discussing about medicines">
          <ul className="flex flex-col gap-1 text-sm">
            {sheet.medicine_flags.map((m, i) => (
              <li key={i}>
                <span className="font-medium">{m.medicine_name} and {m.test_name}: </span>{m.message}{" "}
                <a href={m.source_url} target="_blank" rel="noreferrer" className="text-teal-700 underline print:no-underline">label</a>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="Trends" empty={sheet.trends.length === 0 && "Fewer than two values for every test in this period."}>
        <ul className="grid gap-3 sm:grid-cols-2">
          {sheet.trends.map((t) => (
            <li key={t.test_name} className="flex items-center justify-between gap-3 text-sm">
              <span>
                <span className="font-medium">{t.test_name}</span>
                <span className="block text-xs text-slate-500">
                  {t.points[0].value} → {t.points[t.points.length - 1].value} {t.unit}
                </span>
              </span>
              <Sparkline trend={t} />
            </li>
          ))}
        </ul>
      </Section>

      {sheet.include_medicines && (
        <Section title="Current medicines" empty={sheet.medicines.length === 0 && "No confirmed medicines."}>
          <table className="w-full text-left text-sm">
            <tbody>
              {sheet.medicines.map((m, i) => (
                <tr key={i} className="border-t border-slate-100 first:border-0">
                  <td className="py-1 pr-4 font-medium">{m.name}</td>
                  <td className="pr-4 text-slate-600">{m.generic}</td>
                  <td className="pr-4">{[m.dose_text, m.frequency].filter(Boolean).join(", ")}</td>
                  <td className="text-slate-600">{m.started_on ? `since ${formatDate(m.started_on)}` : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}

      <Section title="Reports included" empty={sheet.reports.length === 0 && "No reports in this period."}>
        <ul className="flex flex-col gap-1 text-sm">
          {sheet.reports.map((r) => (
            <li key={r.document_id}>
              {formatDate(r.report_date)} ·{" "}
              <a href={documentHref(r.document_id)} target="_blank" rel="noreferrer" className="text-teal-700 underline">
                {r.title ?? DOC_TYPE[r.doc_type] ?? "Document"}
              </a>
              {r.title && DOC_TYPE[r.doc_type] ? <span className="text-slate-500"> ({DOC_TYPE[r.doc_type]})</span> : null}
            </li>
          ))}
        </ul>
      </Section>

      <p className="text-xs text-slate-500">
        Values are copied from the reports by YourHealth. Check them against the original reports listed above.
      </p>
    </article>
  );
}

function Section({ title, empty, children }: { title: string; empty?: string | false; children: ReactNode }) {
  const id = `sheet-${title.toLowerCase().replace(/[^a-z]+/g, "-")}`;
  return (
    <section aria-labelledby={id} className="break-inside-avoid">
      <h3 id={id} className="mb-2 font-semibold text-slate-800">{title}</h3>
      {empty ? <p className="text-sm text-slate-500">{empty}</p> : children}
    </section>
  );
}

function range(low: string | null, high: string | null, unit: string): string {
  if (low && high) return `${low}–${high} ${unit}`;
  if (low) return `above ${low} ${unit}`;
  if (high) return `below ${high} ${unit}`;
  return "not printed";
}

/** Small line of the values over time, with the report's range shaded. */
function Sparkline({ trend }: { trend: Sheet["trends"][number] }) {
  const W = 120, H = 32, PAD = 3;
  const values = trend.points.map((p) => Number(p.value));
  const times = trend.points.map((p) => Date.parse(p.observed_on));
  const bounds = [...values, ...[trend.range_low, trend.range_high].filter((v): v is string => v !== null).map(Number)];
  const lo = Math.min(...bounds), hi = Math.max(...bounds);
  const x = (t: number) => PAD + ((t - times[0]) / (times[times.length - 1] - times[0] || 1)) * (W - 2 * PAD);
  const y = (v: number) => H - PAD - ((v - lo) / (hi - lo || 1)) * (H - 2 * PAD);
  const first = trend.points[0], last = trend.points[trend.points.length - 1];
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img"
      aria-label={`${trend.test_name} trend: ${first.value} to ${last.value} ${trend.unit}`} className="shrink-0">
      {trend.range_low !== null && trend.range_high !== null && (
        <rect x={0} width={W} y={y(Number(trend.range_high))} height={y(Number(trend.range_low)) - y(Number(trend.range_high))}
          className="fill-teal-50" />
      )}
      <polyline fill="none" strokeWidth={1.5} className="stroke-teal-700"
        points={values.map((v, i) => `${x(times[i])},${y(v)}`).join(" ")} />
      {values.map((v, i) => <circle key={i} cx={x(times[i])} cy={y(v)} r={2} className="fill-teal-700" />)}
    </svg>
  );
}
