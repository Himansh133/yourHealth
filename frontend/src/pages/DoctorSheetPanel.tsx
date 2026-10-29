import { useCallback, useEffect, useState } from "react";
import { documents, shares as sharesApi, sheets } from "../api/endpoints";
import type { Share, ShareCreated, ShareExpiry, Sheet } from "../api/types";
import SheetView from "../components/SheetView";
import { Button, ErrorAlert, errorMessage } from "../components/ui";
import { formatDate, monthsAgo } from "../format";

const PERIODS = [3, 6, 12];
const EXPIRIES: { value: ShareExpiry; label: string }[] = [
  { value: "1h", label: "1 hour" },
  { value: "24h", label: "24 hours" },
  { value: "7d", label: "7 days" },
];
const STATE_TEXT: Record<Share["state"], string> = {
  active: "Active", expired: "Expired", revoked: "Turned off", locked: "Locked after wrong PINs",
};

export default function DoctorSheetPanel({ profileId, canShare }: { profileId: string; canShare: boolean }) {
  const [months, setMonths] = useState(6);
  const [includeMedicines, setIncludeMedicines] = useState(true);
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");
    sheets.preview(profileId, { from: monthsAgo(months), include_medicines: includeMedicines })
      .then(setSheet)
      .catch((e) => setError(errorMessage(e)));
  }, [profileId, months, includeMedicines]);

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-4 print:hidden">
        <div className="flex flex-col gap-1">
          <label htmlFor="sheet-period" className="text-sm font-medium text-slate-700">Period</label>
          <select id="sheet-period" value={months} onChange={(e) => setMonths(Number(e.target.value))}
            className="rounded-md border border-slate-300 px-3 py-2">
            {PERIODS.map((m) => <option key={m} value={m}>Last {m} months</option>)}
          </select>
        </div>
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input type="checkbox" checked={includeMedicines} onChange={(e) => setIncludeMedicines(e.target.checked)} />
          Include medicines
        </label>
        <Button variant="secondary" onClick={() => window.print()} disabled={!sheet}>Print</Button>
      </div>
      <ErrorAlert>{error}</ErrorAlert>
      {sheet === null && !error && <p className="text-slate-500">Loading…</p>}
      {sheet && <SheetView sheet={sheet} documentHref={documents.fileUrl} />}
      {canShare && <SharePanel profileId={profileId} query={{ from: monthsAgo(months), include_medicines: includeMedicines }} />}
    </section>
  );
}

function SharePanel({ profileId, query }: { profileId: string; query: { from: string; include_medicines: boolean } }) {
  const [list, setList] = useState<Share[]>([]);
  const [expiry, setExpiry] = useState<ShareExpiry>("24h");
  const [created, setCreated] = useState<ShareCreated | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(() => {
    sharesApi.list(profileId).then(setList).catch((e) => setError(errorMessage(e)));
  }, [profileId]);
  useEffect(refresh, [refresh]);

  async function create() {
    setError("");
    setBusy(true);
    try {
      setCreated(await sharesApi.create(profileId, { ...query, expires_in: expiry }));
      refresh();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function revoke(id: string) {
    setError("");
    try {
      await sharesApi.revoke(id);
      refresh();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  return (
    <section aria-labelledby="share-title" className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 print:hidden">
      <h3 id="share-title" className="font-semibold">Share with a doctor</h3>
      <p className="text-sm text-slate-600">
        The doctor scans the QR code and types the PIN you tell them. They see this sheet as it is now, and the reports
        listed on it. Nothing else.
      </p>
      <div className="flex flex-wrap items-center gap-4">
        <fieldset className="flex gap-4 text-sm">
          <legend className="sr-only">Link works for</legend>
          {EXPIRIES.map((e) => (
            <label key={e.value} className="flex items-center gap-1">
              <input type="radio" name="expiry" value={e.value} checked={expiry === e.value} onChange={() => setExpiry(e.value)} />
              {e.label}
            </label>
          ))}
        </fieldset>
        <Button onClick={create} disabled={busy}>{busy ? "Creating…" : "Create share link"}</Button>
      </div>
      <ErrorAlert>{error}</ErrorAlert>

      {created && (
        <section aria-label="New share link" className="flex flex-wrap items-center gap-4 rounded-md bg-teal-50 p-4">
          <img src={`data:image/png;base64,${created.qr_png_base64}`} alt="QR code for the share link"
            className="h-40 w-40 bg-white" />
          <div className="flex flex-col gap-1 text-sm">
            <p>PIN to tell the doctor:</p>
            <p className="text-3xl font-semibold tracking-widest">{created.pin}</p>
            <p className="text-slate-600">Shown only now. Works until {formatDateTime(created.expires_at)}.</p>
            <p className="break-all text-xs text-slate-500">{created.url}</p>
          </div>
        </section>
      )}

      {list.length > 0 && (
        <ul className="flex flex-col gap-2 text-sm">
          {list.map((s) => (
            <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-2">
              <span>
                {STATE_TEXT[s.state]} · made {formatDateTime(s.created_at)} ·{" "}
                {s.opens === 0 ? "not opened yet" : `opened ${s.opens} ${s.opens === 1 ? "time" : "times"}, last ${formatDateTime(s.last_opened_at!)}`}
              </span>
              {s.state === "active" && <Button variant="secondary" onClick={() => revoke(s.id)}>Turn off</Button>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** "29 Oct 2026, 11:42" in the viewer's own time zone. */
function formatDateTime(iso: string): string {
  const d = new Date(iso);
  const pad = (x: number) => String(x).padStart(2, "0");
  const local = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  return `${formatDate(local)}, ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
