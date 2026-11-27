import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { allergies, type Allergies, type Allergy } from '../api/doctor';
import { Button, ErrorAlert, TextField, errorMessage } from '../components/ui';

export function AllergySummary({ data }: { data: Allergies }) {
  return <div><p className="font-medium">{data.status === 'unknown' ? 'No allergy information recorded. Ask the patient.'
    : data.status === 'none_known_confirmed' ? `Patient confirmed no known allergies${data.confirmed_at ? ` on ${new Date(data.confirmed_at).toLocaleDateString()}` : ''}.`
      : 'Recorded allergies'}</p></div>;
}

export default function AllergiesPanel({ profileId, canEdit }: { profileId: string; canEdit: boolean }) {
  const [data, setData] = useState<Allergies | null>(null);
  const [name, setName] = useState(''); const [reaction, setReaction] = useState('');
  const [severity, setSeverity] = useState<Allergy['severity']>('unknown');
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const load = useCallback(async () => setData(await allergies.list(profileId)), [profileId]);
  useEffect(() => { void load().catch((e) => setError(errorMessage(e))); }, [load]);
  async function act(work: () => Promise<unknown>) { setBusy(true); setError(''); try { await work(); await load(); } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); } }
  async function submit(e: FormEvent) {
    e.preventDefault(); await act(async () => {
      const body = { substance_text: name, reaction_text: reaction || null, severity };
      if (editing) await allergies.update(profileId, editing, body); else await allergies.add(profileId, body);
      setName(''); setReaction(''); setSeverity('unknown'); setEditing(null);
    });
  }
  return <section className="flex flex-col gap-5"><h2 className="text-xl font-semibold">Allergies</h2><ErrorAlert>{error}</ErrorAlert>
    {!data && !error && <p>Loading allergies…</p>}{data && <AllergySummary data={data} />}
    {data?.entries.map((entry) => <article key={entry.id} className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="font-semibold">{entry.substance_text}</h3><p>{entry.reaction_text || 'Reaction not recorded'} · Severity: {entry.severity}</p>
      <p className="mt-1 text-sm text-slate-600">{entry.source === 'document' ? 'Found in report' : 'Patient entry'} · {entry.confirmed_by_user ? 'Confirmed by patient' : 'Not confirmed by patient'}</p>
      {entry.source_document_id && <a className="text-sm text-teal-700 underline" href={`/api/v1/documents/${entry.source_document_id}/file`} target="_blank" rel="noreferrer">Open source report</a>}
      {canEdit && <div className="mt-3 flex flex-wrap gap-3">{!entry.confirmed_by_user && <Button disabled={busy} onClick={() => void act(() => allergies.update(profileId, entry.id, { confirmed_by_user: true }))}>Confirm entry</Button>}
        <Button variant="secondary" disabled={busy} onClick={() => { setEditing(entry.id); setName(entry.substance_text); setReaction(entry.reaction_text ?? ''); setSeverity(entry.severity); }}>Edit</Button>
        <Button variant="secondary" disabled={busy} onClick={() => void act(() => allergies.remove(profileId, entry.id))}>Remove</Button></div>}
    </article>)}
    {canEdit && <><div className="flex flex-wrap gap-3"><Button variant="secondary" disabled={busy} onClick={() => void act(() => allergies.status(profileId, 'none_known_confirmed'))}>Confirm no known allergies</Button>
      <Button variant="secondary" disabled={busy} onClick={() => void act(() => allergies.status(profileId, 'unknown'))}>Mark information unknown</Button></div>
      <form onSubmit={submit} className="rounded-lg border border-slate-200 bg-white p-5"><h3 className="mb-4 font-semibold">{editing ? 'Edit allergy' : 'Add an allergy'}</h3>
        <fieldset disabled={busy} className="flex flex-col gap-4"><TextField label="Substance or medicine" required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} />
          <TextField label="Reaction (optional)" maxLength={500} value={reaction} onChange={(e) => setReaction(e.target.value)} />
          <label>Severity<select className="ml-3 min-h-11 rounded border border-slate-300 bg-white px-3" value={severity} onChange={(e) => setSeverity(e.target.value as Allergy['severity'])}>
            <option value="unknown">Unknown</option><option value="mild">Mild</option><option value="moderate">Moderate</option><option value="severe">Severe</option></select></label>
          <div className="flex gap-3"><Button type="submit">{busy ? 'Saving…' : 'Save allergy'}</Button>{editing && <Button type="button" variant="secondary" onClick={() => { setEditing(null); setName(''); setReaction(''); }}>Cancel edit</Button>}</div>
        </fieldset>
      </form></>}
  </section>;
}
