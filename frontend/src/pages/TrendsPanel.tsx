import { useEffect, useId, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from "recharts";
import { labs } from "../api/endpoints";
import type { Flag, Trend, TrendPoint } from "../api/types";
import { Button, ErrorAlert, errorMessage } from "../components/ui";
import { formatDate } from "../format";

// Single series per chart: the card title names it, so no legend. Status colours always come
// with a word or symbol (never colour alone). Values come straight from SQL, never from an LLM.
const COLOR = {
  line: "#0f766e", // teal-700, the series
  out: "#dc2626", // red-600, status: outside the printed range
  noRange: "#94a3b8", // slate-400, status: no range printed
  band: "#e2e8f0", // slate-200, recessive reference band
  grid: "#e2e8f0",
  axis: "#64748b", // slate-500 text
  surface: "#ffffff",
};

const FLAG_TEXT: Record<Flag, string> = {
  high: "▲ Above range",
  low: "▼ Below range",
  normal: "✓ In range",
  no_range: "Range not printed on this report",
  non_numeric: "—",
};

function rangeText(p: TrendPoint): string {
  if (p.range_low != null && p.range_high != null) return `${p.range_low} – ${p.range_high}`;
  if (p.range_high != null) return `< ${p.range_high}`;
  if (p.range_low != null) return `> ${p.range_low}`;
  return "Range not printed on this report";
}

function valueText(p: TrendPoint, unit: string): string {
  return `${p.qualifier ?? ""}${p.value} ${unit}`;
}

function pointColor(p: TrendPoint): string {
  if (p.flag === "high" || p.flag === "low") return COLOR.out;
  if (p.flag === "no_range") return COLOR.noRange;
  return COLOR.line;
}

export default function TrendsPanel({ profileId }: { profileId: string }) {
  const [trends, setTrends] = useState<Trend[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    labs.trends(profileId).then(setTrends).catch((e) => setError(errorMessage(e)));
  }, [profileId]);

  if (error) return <ErrorAlert>{error}</ErrorAlert>;
  if (!trends) return <p className="text-slate-500">Loading…</p>;
  if (trends.length === 0)
    return <p className="text-slate-600">Charts appear when a test shows up in two or more reports.</p>;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {trends.map((t) => <TrendCard key={t.test.loinc_code} trend={t} />)}
    </div>
  );
}

function TrendCard({ trend }: { trend: Trend }) {
  const { test, points, latest } = trend;
  const [showTable, setShowTable] = useState(false);
  const titleId = useId();
  const navigate = useNavigate();
  const openSource = (p: TrendPoint) => navigate(`/documents/${p.document_id}/review`);
  const data = points.map((p) => ({ ...p, label: formatDate(p.observed_on) }));
  const flagTone = latest.flag === "high" || latest.flag === "low" ? "text-red-700" : "text-slate-600";

  return (
    <article aria-labelledby={titleId} className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <header>
        <h2 id={titleId} className="text-lg font-semibold">{test.name}</h2>
        {test.name_hi && <p className="text-sm text-slate-500">{test.name_hi}</p>}
      </header>

      <div>
        <p className="flex items-baseline gap-1">
          <span className="text-3xl font-semibold tabular-nums">{latest.qualifier ?? ""}{latest.value}</span>
          <span className="text-slate-500">{test.unit}</span>
        </p>
        <p className="text-sm text-slate-500">Latest · {formatDate(latest.observed_on)}</p>
        <p className={`text-sm font-medium ${flagTone}`}>{FLAG_TEXT[latest.flag]}</p>
        {latest.low_confidence && (
          <Link to={`/documents/${latest.document_id}/review`} className="text-sm font-medium text-amber-700 underline">
            Latest value not checked yet
          </Link>
        )}
      </div>

      <div className="h-44" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke={COLOR.grid} />
            {(latest.range_low != null || latest.range_high != null) && (
              <ReferenceArea y1={latest.range_low ?? undefined} y2={latest.range_high ?? undefined}
                fill={COLOR.band} fillOpacity={0.6} ifOverflow="extendDomain" />
            )}
            <XAxis dataKey="label" tick={{ fill: COLOR.axis, fontSize: 11 }} tickLine={false} axisLine={{ stroke: COLOR.grid }} />
            <YAxis width={40} tick={{ fill: COLOR.axis, fontSize: 11 }} tickLine={false} axisLine={false}
              domain={["auto", "auto"]} />
            <Tooltip content={<PointTooltip unit={test.unit} />} cursor={{ stroke: COLOR.axis, strokeDasharray: "3 3" }} />
            <Line type="linear" dataKey="value" stroke={COLOR.line} strokeWidth={2} isAnimationActive={false}
              dot={renderDot(4, openSource)} activeDot={renderDot(6, openSource)} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-slate-500">
        Shaded band: range printed on the latest report. Tap a point to open that report.
      </p>

      <div>
        <Button variant="link" className="text-sm" aria-expanded={showTable} onClick={() => setShowTable(!showTable)}>
          {showTable ? "Hide table" : "Show values as a table"}
        </Button>
        {showTable && (
          <table aria-label={`${test.name} values`} className="mt-2 w-full text-sm">
            <thead className="text-left text-slate-600">
              <tr><th className="py-1 font-medium">Date</th><th className="py-1 font-medium">Value</th>
                <th className="py-1 font-medium">Range</th><th className="py-1 font-medium">Flag</th></tr>
            </thead>
            <tbody>
              {points.map((p) => (
                <tr key={p.lab_result_id} className="border-t border-slate-100">
                  <td className="py-1">
                    <Link to={`/documents/${p.document_id}/review`} className="text-teal-700 underline">{formatDate(p.observed_on)}</Link>
                  </td>
                  <td className="py-1 tabular-nums">{valueText(p, test.unit)}</td>
                  <td className="py-1 text-slate-600">{rangeText(p)}</td>
                  <td className="py-1">
                    {p.flag === "no_range" ? "—" : FLAG_TEXT[p.flag]}
                    {p.low_confidence && <span className="block text-xs text-amber-700">Not checked yet</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </article>
  );
}

type DotRenderProps = { index: number; cx?: number; cy?: number; payload?: TrendPoint };

// Recharts types render-prop arguments as unknown; this is the one place we narrow them.
function renderDot(r: number, onClick: (p: TrendPoint) => void) {
  return (props: unknown) => {
    const p = props as DotRenderProps;
    return <PointDot key={p.index} cx={p.cx} cy={p.cy} payload={p.payload} r={r} onClick={onClick} />;
  };
}

type DotProps = { cx?: number; cy?: number; r?: number; payload?: TrendPoint; onClick: (p: TrendPoint) => void };

function PointDot({ cx, cy, r = 4, payload, onClick }: DotProps) {
  if (cx == null || cy == null || !payload) return null;
  const color = pointColor(payload);
  return (
    <g style={{ cursor: "pointer" }} onClick={() => onClick(payload)}>
      {/* invisible larger hit target */}
      <circle cx={cx} cy={cy} r={12} fill="transparent" />
      <circle cx={cx} cy={cy} r={r} strokeWidth={2}
        // Hollow = not checked yet; a surface ring separates the dot from the line.
        fill={payload.low_confidence ? COLOR.surface : color}
        stroke={payload.low_confidence ? color : COLOR.surface} />
    </g>
  );
}

function PointTooltip({ active, payload, unit }: TooltipProps<number, string> & { unit: string }) {
  const p = active && payload?.[0]?.payload as TrendPoint | undefined;
  if (!p) return null;
  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-slate-900">{formatDate(p.observed_on)}</p>
      <p className="tabular-nums text-slate-900">{valueText(p, unit)}</p>
      <p className="text-slate-600">Range: {rangeText(p)}</p>
      {(p.flag === "high" || p.flag === "low") && <p className="font-medium text-red-700">{FLAG_TEXT[p.flag]}</p>}
      {p.low_confidence && <p className="text-amber-700">Not checked yet</p>}
    </div>
  );
}
