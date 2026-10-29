import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { chat } from "../api/endpoints";
import type { ChatAnswer, ChatSource, Lang } from "../api/types";
import { Button, ErrorAlert, errorMessage } from "../components/ui";

type Turn = { question: string; answer: ChatAnswer };

const LANGS: { value: Lang; label: string }[] = [
  { value: "en", label: "English" },
  { value: "hi", label: "हिंदी" },
];

export default function ChatPanel({ profileId, profileName }: { profileId: string; profileName: string }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [lang, setLang] = useState<Lang>("en");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");

  async function ask(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    setError("");
    setAsking(true);
    try {
      const answer = await chat.ask(profileId, q, lang);
      setTurns((prev) => [...prev, { question: q, answer }]);
      setQuestion("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setAsking(false);
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <p className="text-sm text-slate-600">
        Answers come only from {profileName}'s uploaded reports, with a link to where each value came from. This is not
        medical advice. For now you can ask about test values and trends, like "What was the latest HbA1c?"
      </p>

      {turns.map((t, i) => (
        <div key={i} className="flex flex-col gap-2">
          <p className="self-end rounded-lg bg-teal-700 px-4 py-2 text-white">{t.question}</p>
          <AnswerCard answer={t.answer} />
        </div>
      ))}

      <form onSubmit={ask} className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-white p-4">
        <label htmlFor="chat-question" className="text-sm font-medium text-slate-700">
          Ask about {profileName}'s reports
        </label>
        <textarea
          id="chat-question"
          rows={2}
          maxLength={500}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) ask(e);
          }}
          className="rounded-md border border-slate-300 px-3 py-2 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600"
        />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <fieldset className="flex gap-4 text-sm">
            <legend className="sr-only">Answer language</legend>
            {LANGS.map((l) => (
              <label key={l.value} className="flex items-center gap-1">
                <input type="radio" name="lang" value={l.value} checked={lang === l.value} onChange={() => setLang(l.value)} />
                {l.label}
              </label>
            ))}
          </fieldset>
          <Button type="submit" disabled={asking || !question.trim()}>
            {asking ? "Thinking…" : "Ask"}
          </Button>
        </div>
        {asking && <p role="status" className="text-sm text-slate-500">Looking through the reports…</p>}
      </form>
      <ErrorAlert>{error}</ErrorAlert>
    </section>
  );
}

function AnswerCard({ answer }: { answer: ChatAnswer }) {
  const byId = new Map(answer.sources.map((s) => [s.id, s]));
  return (
    <article aria-label="Answer" className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4">
      <p className={answer.answerable && !answer.fallback ? "font-medium" : "text-slate-600"}>{answer.summary}</p>
      {answer.claims.length > 0 && (
        <ul className="flex flex-col gap-2">
          {answer.claims.map((c, i) => (
            <li key={i} className="flex flex-wrap items-baseline gap-2 text-sm">
              <span>{answer.fallback ? factText(c.text) : c.text}</span>
              {c.evidence_ids.map((id) => byId.get(id)).filter((s): s is ChatSource => !!s).map((s) => (
                <SourceChip key={s.id} source={s} />
              ))}
            </li>
          ))}
        </ul>
      )}
      {answer.missing_info.length > 0 && (
        <ul className="list-disc pl-5 text-sm text-slate-600">
          {answer.missing_info.map((m, i) => <li key={i}>{m}</li>)}
        </ul>
      )}
      {answer.doctor_note && (
        <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <span className="font-medium">For the doctor visit: </span>
          {answer.doctor_note}
        </p>
      )}
    </article>
  );
}

function SourceChip({ source }: { source: ChatSource }) {
  return (
    <Link
      to={`/documents/${source.document_id}/review`}
      className="rounded-full border border-teal-200 bg-teal-50 px-2 py-0.5 text-xs text-teal-800 hover:bg-teal-100"
    >
      {source.page_no ? `Report, page ${source.page_no}` : "Report"}
    </Link>
  );
}

/** Fallback facts arrive as evidence lines: "lab_result | HbA1c 7.2 % (ref 4.0-5.6) HIGH | 2026-06-14 | p.2". */
function factText(text: string): string {
  return text.replace(/^lab_result \| /, "").split(" | ").join(" · ");
}
