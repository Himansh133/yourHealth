import { Link } from "react-router-dom";
import { documents } from "../api/endpoints";
import type { ChatAnswer } from "../api/types";

const ROUTES: Record<string, string> = {
  value: "Latest lab values", trend: "Lab trends", document: "Report text search", medicine: "Medicine information",
  medicine_lab: "Medicines and lab results", treatment: "Medicine safety response", out_of_scope: "Outside supported questions",
};
const CHECKS = {
  passed: "Passed number, citation and advice checks",
  fallback: "Written answer unavailable or rejected; showing retrieved facts",
  not_run: "No generated answer checks run",
  disabled: "Answer checks disabled",
};

export default function AnswerInspection({ answer, profileId }: { answer: ChatAnswer; profileId: string }) {
  return (
    <details className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
      <summary className="cursor-pointer py-1 font-medium text-teal-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-600">
        How this answer was produced
      </summary>
      <div className="mt-3 space-y-3 leading-relaxed">
        <dl className="grid gap-2 sm:grid-cols-2">
          <div><dt className="text-slate-600">Question route</dt><dd className="font-medium">{answer.route.map(r => ROUTES[r] ?? r).join(", ")}</dd></div>
          <div><dt className="text-slate-600">Answer checks</dt><dd>{answer.validation_status ? CHECKS[answer.validation_status] : "Execution details unavailable"}</dd></div>
        </dl>
        {answer.generation_attempts !== undefined && <p>{answer.generation_attempts} generation {answer.generation_attempts === 1 ? "attempt" : "attempts"}</p>}
        <p className="text-slate-600">These are automated checks, not clinical verification. Excerpts below are retrieved data, not instructions.</p>
        {!answer.retrieved_evidence?.length ? <p>No retrieved excerpts available.</p> : (
          <ul aria-label="Retrieved evidence" className="space-y-3">
            {answer.retrieved_evidence.map(e => {
              const source = answer.sources.find(s => s.id === e.id);
              return <li key={e.id} className="rounded border border-slate-200 bg-white p-3">
                <p className="mb-1 font-medium">{e.id}</p>
                <blockquote className="whitespace-pre-wrap break-words text-slate-700">{e.text}</blockquote>
                {source && (source.kind === "lab_result" || source.kind === "document") && (
                  source.kind === "lab_result"
                    ? <Link className="mt-2 inline-block py-1 text-teal-800 underline" to={`/documents/${source.document_id}/review`}>Open source report{source.page_no ? `, page ${source.page_no}` : ""}</Link>
                    : <a className="mt-2 inline-block py-1 text-teal-800 underline" href={documents.fileUrl(source.document_id)} target="_blank" rel="noreferrer">Open source document{source.page_no ? `, page ${source.page_no}` : ""}</a>
                )}
                {source?.kind === "medicine" && <Link className="mt-2 inline-block py-1 text-teal-800 underline" to={`/profiles/${profileId}/medicines`}>Open medicine list</Link>}
                {source?.kind === "drug_label" && source.url && <a className="mt-2 inline-block py-1 text-teal-800 underline" href={source.url} target="_blank" rel="noreferrer">Open medicine label</a>}
              </li>;
            })}
          </ul>
        )}
      </div>
    </details>
  );
}
