import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { doctorAccess, type Grant } from "../api/doctor";
import { doctors } from "../api/endpoints";
import type { Doctor, VerificationStatus } from "../api/types";
import { Button, ErrorAlert, TextField, errorMessage } from "../components/ui";

const STATUS: Record<VerificationStatus, { title: string; description: string }> = {
  unverified: { title: "Verification pending", description: "An admin must check your registration before approving your account. You cannot request or view patient records yet." },
  verified: { title: "Registration verified", description: "Your registration has been approved. Every patient must still approve access before you can view their records." },
  rejected: { title: "Registration not approved", description: "Your registration was not approved. Contact the administrator to review your registration details." },
  suspended: { title: "Account access suspended", description: "Patient access is suspended. Contact the administrator for a review." },
};

export default function DoctorHomePage() {
  const [grants, setGrants] = useState<Grant[]>([]);
  const [patientCode, setPatientCode] = useState("");
  const [reason, setReason] = useState("");
  const [hours, setHours] = useState(24);
  const [clinicCode, setClinicCode] = useState("");
  const [notice, setNotice] = useState("");
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    setBusy(true);
    setError("");
    try { const d = await doctors.me(); setDoctor(d); if (d.verification_status === "verified") setGrants(await doctorAccess.grants()); else setGrants([]); }
    catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  const status = doctor ? STATUS[doctor.verification_status] : null;

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <div><p className="text-sm font-medium text-teal-800">Doctor portal</p>
        <h1 className="mt-1 text-2xl font-semibold">{doctor ? `Welcome, ${doctor.full_name}` : "Your doctor account"}</h1></div>
      <ErrorAlert>{error}</ErrorAlert>
      {busy && !doctor && <p className="text-slate-600">Loading account…</p>}
      {doctor && status && <section className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-xl font-semibold">{status.title}</h2>
        <p className="mt-2 text-slate-600">{status.description}</p>
        <dl className="mt-6 grid gap-4 sm:grid-cols-2">
          {[["Registration number", doctor.registration_number], ["Council", doctor.registration_council],
            ["Specialty", doctor.specialty ?? "Not provided"], ["Clinic", doctor.clinic_name ?? "Not provided"]]
            .map(([label, value]) => <div key={label}><dt className="text-sm text-slate-600">{label}</dt>
              <dd className="break-words font-medium">{value || "Not provided"}</dd></div>)}
        </dl>
      </section>}
      <div><Button variant="secondary" className="min-h-11" disabled={busy} onClick={() => void refresh()}>
        {busy ? "Refreshing…" : "Refresh status"}</Button></div>
      {notice && <p role="status" className="rounded bg-teal-50 p-3 text-teal-900">{notice}</p>}
      {doctor?.verification_status === "verified" && <>
        <section className="rounded-lg border border-slate-200 bg-white p-5"><h2 className="mb-4 text-xl font-semibold">Request patient access</h2>
          <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); setBusy(true); setError(""); setNotice("");
            doctorAccess.lookup(patientCode, reason, hours).then((r) => setNotice(r.message)).catch((e) => setError(errorMessage(e))).finally(() => setBusy(false)); }}>
            <TextField label="Patient code" required maxLength={30} value={patientCode} onChange={(e) => setPatientCode(e.target.value)} hint="Ask the patient for their YH code." />
            <TextField label="Reason for access" required maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
            <label>Requested duration <select className="min-h-11 rounded border border-slate-300 bg-white px-3" value={hours} onChange={(e) => setHours(Number(e.target.value))}><option value={1}>1 hour</option><option value={24}>24 hours</option><option value={168}>7 days</option></select></label>
            <Button disabled={busy} type="submit">Send access request</Button>
          </form>
        </section>
        <section className="rounded-lg border border-slate-200 bg-white p-5"><h2 className="mb-3 font-semibold">Use a clinic code</h2>
          <p className="mb-3 text-sm text-slate-600">Enter the patient's code above and the one-time code they show you at the clinic.</p>
          <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); setBusy(true); setError("");
            doctorAccess.redeem(patientCode, clinicCode).then(async () => { setGrants(await doctorAccess.grants()); setNotice("Clinic access activated."); setClinicCode(""); }).catch((e) => setError(errorMessage(e))).finally(() => setBusy(false)); }}>
            <TextField label="Six-digit clinic code" required inputMode="numeric" pattern="[0-9]{6}" minLength={6} maxLength={6} value={clinicCode} onChange={(e) => setClinicCode(e.target.value)} />
            <Button disabled={busy || !patientCode} type="submit">Activate clinic access</Button>
          </form>
        </section>
        <section><h2 className="mb-3 text-xl font-semibold">Patients with active access</h2>
          {grants.length === 0 && <p className="text-slate-600">No active patient access. Requests appear here after the patient approves.</p>}
          <ul className="flex flex-col gap-3">{grants.map((g) => <li key={g.id} className="rounded-lg border border-slate-200 bg-white p-4">
            <Link to={`/doctor/patients/${g.profile_id}`} className="font-semibold text-teal-700 underline">{g.display_name}</Link>
            <p className="text-sm text-slate-600">Access expires {new Date(g.expires_at).toLocaleString()}</p>
          </li>)}</ul>
        </section>
      </>}

    </div>
  );
}
