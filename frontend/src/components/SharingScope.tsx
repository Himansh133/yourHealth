import type { Scope } from '../api/doctor';
import type { Doc } from '../api/types';

export default function SharingScope({ scope, setScope, hours, setHours, docs, disabled = false }: {
  scope: Scope; setScope: (scope: Scope) => void; hours: number; setHours: (hours: number) => void; docs: Doc[]; disabled?: boolean;
}) {
  return <fieldset disabled={disabled} className="flex flex-col gap-3 rounded-md border border-slate-200 p-4">
    <legend className="px-1 font-medium">Choose what to share</legend>
    <div className="flex flex-wrap gap-4">{(['allergies', 'medicines', 'labs', 'documents'] as const).map((category) =>
      <label key={category} className="flex min-h-11 items-center gap-2 capitalize"><input type="checkbox" checked={scope[category]}
        onChange={(e) => setScope({ ...scope, [category]: e.target.checked })} />{category}</label>)}</div>
    <label className="flex flex-wrap items-center gap-3">Access duration
      <select className="min-h-11 rounded border border-slate-300 bg-white px-3" value={hours} onChange={(e) => setHours(Number(e.target.value))}>
        <option value={1}>1 hour</option><option value={24}>24 hours</option><option value={168}>7 days</option>
      </select>
    </label>
    {docs.length > 0 && <details><summary className="cursor-pointer py-2 font-medium">Hide individual reports</summary>
      <p className="text-sm text-slate-600">Hidden reports and information extracted from them will not be shared.</p>
      {docs.map((doc) => <label key={doc.id} className="flex min-h-11 items-center gap-2"><input type="checkbox"
        checked={scope.excluded_document_ids.includes(doc.id)} onChange={(e) => setScope({ ...scope, excluded_document_ids: e.target.checked
          ? [...scope.excluded_document_ids, doc.id] : scope.excluded_document_ids.filter((id) => id !== doc.id) })} />
        Hide {doc.original_filename ?? doc.lab_name ?? 'Report'}</label>)}
    </details>}
  </fieldset>;
}
