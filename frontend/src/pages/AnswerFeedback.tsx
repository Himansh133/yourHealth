import { useState } from "react";
import { chat } from "../api/endpoints";
import type { FeedbackCategory } from "../api/types";
import { Button, ErrorAlert, errorMessage } from "../components/ui";

const OPTIONS: { value: FeedbackCategory; label: string }[] = [
  { value: "helpful", label: "Helpful" }, { value: "too_long", label: "Too long" },
  { value: "wrong_evidence", label: "Wrong evidence" }, { value: "missed_question", label: "Missed my question" },
];
export default function AnswerFeedback({ profileId, answerId }: { profileId: string; answerId: string }) {
  const [selected, setSelected] = useState<FeedbackCategory | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save(category: FeedbackCategory) {
    setBusy(true);
    setError("");
    try { const result = await chat.feedback(profileId, answerId, category); setSelected(result.category); }
    catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  return <fieldset className="border-t border-slate-100 pt-3">
    <legend className="text-sm font-medium text-slate-700">Was this answer useful?</legend>
    <div className="mt-2 flex flex-wrap gap-2">{OPTIONS.map(o => <Button type="button" key={o.value} variant="secondary" aria-pressed={selected === o.value} disabled={busy}
      className={`min-h-11 text-sm ${selected === o.value ? "border-teal-700 bg-teal-50 text-teal-900" : ""}`} onClick={() => void save(o.value)}>{o.label}</Button>)}</div>
    {busy ? <p role="status" className="mt-2 text-sm text-slate-600">Saving feedback…</p> : selected && <p role="status" className="mt-2 text-sm text-teal-800">Feedback saved. You can change your selection.</p>}
    <div className="mt-2"><ErrorAlert>{error}</ErrorAlert></div>
  </fieldset>;
}
