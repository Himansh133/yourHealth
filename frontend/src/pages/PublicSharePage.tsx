import { useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";
import { publicShare } from "../api/endpoints";
import type { Sheet } from "../api/types";
import SheetView from "../components/SheetView";
import { Button, ErrorAlert, errorMessage } from "../components/ui";

/** What a doctor sees after scanning the QR code: a PIN box, then the shared sheet. No account needed. */
export default function PublicSharePage() {
  const { token = "" } = useParams();
  const [pin, setPin] = useState("");
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function open(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await publicShare.unlock(token, pin);
      setSheet(await publicShare.sheet(token));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-8">
      <p className="text-sm font-semibold text-teal-800">YourHealth · shared health summary</p>
      {sheet ? (
        <SheetView sheet={sheet} documentHref={(id) => publicShare.documentUrl(token, id)} />
      ) : (
        <form onSubmit={open} className="flex max-w-xs flex-col gap-3 rounded-lg border border-slate-200 bg-white p-6">
          <label htmlFor="share-pin" className="text-sm font-medium text-slate-700">PIN</label>
          <input id="share-pin" inputMode="numeric" autoComplete="off" maxLength={4} value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
            className="rounded-md border border-slate-300 px-3 py-2 text-2xl tracking-widest focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600" />
          <p className="text-xs text-slate-500">Ask the patient or their family for the 4-digit PIN.</p>
          <Button type="submit" disabled={busy || pin.length !== 4}>{busy ? "Opening…" : "Open"}</Button>
          <ErrorAlert>{error}</ErrorAlert>
        </form>
      )}
    </main>
  );
}
