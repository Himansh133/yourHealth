import { useCallback, useEffect, useState } from 'react';
import { access, defaultScope, type AccessEvent, type AccessRequest, type ClinicCode, type PatientGrant } from '../api/doctor';
import { documents } from '../api/endpoints';
import type { Doc, Profile } from '../api/types';
import SharingScope from '../components/SharingScope';
import { Button, ErrorAlert, errorMessage } from '../components/ui';

export default function AccessPanel({ profile }: { profile: Profile }) {
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [grants, setGrants] = useState<PatientGrant[]>([]);
  const [history, setHistory] = useState<AccessEvent[]>([]);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [scope, setScope] = useState(defaultScope);
  const [hours, setHours] = useState(24);
  const [clinic, setClinic] = useState<ClinicCode | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const canEdit = profile.role !== 'viewer';
  const load = useCallback(async () => {
    const [r, g, h, d] = await Promise.all([access.requests(), access.grants(profile.id), access.history(profile.id), documents.list(profile.id)]);
    setRequests(r.filter((item) => item.profile_id === profile.id && item.status === 'pending'));
    setGrants(g); setHistory(h); setDocs(d); setLoaded(true);
  }, [profile.id]);
  useEffect(() => { void load().catch((e) => setError(errorMessage(e))); }, [load]);
  async function act(action: () => Promise<unknown>, message: string) {
    setBusy(true); setError(''); setNotice('');
    try { await action(); await load(); setNotice(message); } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  const active = grants.filter((g) => !g.revoked_at && Date.parse(g.expires_at) > Date.now());
  return <section className="flex flex-col gap-5">
    <div><h2 className="text-xl font-semibold">Who can see my records</h2><p className="mt-2 text-slate-600">Your patient code: <strong className="font-mono">{profile.public_code}</strong>.
      This code only lets a verified doctor request your permission.</p></div>
    <ErrorAlert>{error}</ErrorAlert>{notice && <p role="status" className="rounded bg-teal-50 p-3 text-teal-900">{notice}</p>}
    <div><Button variant="secondary" disabled={busy} onClick={() => void act(load, 'Access information refreshed.')}>Refresh requests</Button></div>
    {!loaded && !error && <p>Loading access information…</p>}
    {canEdit && <SharingScope scope={scope} setScope={setScope} hours={hours} setHours={setHours} docs={docs} disabled={busy} />}
    <section><h3 className="mb-3 font-semibold">Pending requests</h3>
      {loaded && requests.length === 0 && <p className="text-slate-600">No pending requests.</p>}
      {requests.map((r) => <article key={r.id} className="mb-3 rounded-lg border border-slate-200 bg-white p-4">
        <h4 className="font-medium">{r.doctor.full_name}</h4><p className="text-sm text-slate-600">{r.doctor.registration_number} · {r.doctor.registration_council}</p>
        <p className="mt-2">Reason: {r.reason_text || 'Not provided'}</p><p className="text-sm">Requested {r.requested_hours} hours. Respond before {new Date(r.expires_at).toLocaleString()}.</p>
        {canEdit && <div className="mt-3 flex gap-3"><Button disabled={busy} onClick={() => void act(() => access.approve(r.id, hours, scope), 'Access approved with your selected sharing settings.')}>Approve selected access</Button>
          <Button variant="secondary" disabled={busy} onClick={() => void act(() => access.deny(r.id), 'Request denied.')}>Deny</Button></div>}
      </article>)}
    </section>
    <section><h3 className="mb-3 font-semibold">Active access</h3>{loaded && active.length === 0 && <p className="text-slate-600">No doctors currently have access.</p>}
      {active.map((g) => <article key={g.id} className="mb-3 rounded-lg border border-slate-200 bg-white p-4">
        <h4 className="font-medium">{g.doctor.full_name}</h4><p className="text-sm">Registration: {g.doctor.registration_number}</p>
        <p>Expires {new Date(g.expires_at).toLocaleString()}</p><p className="text-sm text-slate-600">Shared: {(['allergies','medicines','labs','documents'] as const).filter((k) => g.scope[k]).join(', ') || 'No categories'}</p>
        {canEdit && <Button variant="secondary" className="mt-3" disabled={busy} onClick={() => void act(() => access.revoke(g.id), 'Access revoked immediately.')}>Revoke access</Button>}
      </article>)}
    </section>
    {canEdit && <section className="rounded-lg border border-teal-200 bg-teal-50 p-5"><h3 className="font-semibold">At the clinic</h3>
      <p className="my-2 text-sm">Creating and showing a clinic code authorizes a verified doctor to access the categories and duration selected above. It expires in 10 minutes and can be used once.</p>
      <Button disabled={busy} onClick={() => void act(async () => setClinic(await access.clinic(profile.id, hours, scope)), 'Clinic code created.')}>Create clinic code</Button>
      {clinic && <div className="mt-4"><p className="font-mono text-3xl tracking-widest">{clinic.code}</p><p className="text-sm">Expires {new Date(clinic.expires_at).toLocaleString()}</p>
        <img className="mt-3 h-48 w-48" alt="Clinic code QR for the doctor" src={`data:image/png;base64,${clinic.qr_png_base64}`} /></div>}
    </section>}
    <section><h3 className="mb-3 font-semibold">Access history</h3>{history.length === 0 && <p className="text-slate-600">No access events recorded.</p>}
      <ul className="divide-y divide-slate-200">{history.map((event) => <li key={event.id} className="py-3 text-sm"><strong>{event.doctor_name || 'Account activity'}</strong> · {event.action.replaceAll('.', ' ').replaceAll('_', ' ')}
        <span className="block text-slate-600">{new Date(event.at).toLocaleString()} · {event.outcome}</span></li>)}</ul>
    </section>
  </section>;
}
