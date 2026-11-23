import { useEffect, useState } from "react";
import { admin } from "../api/endpoints";
import type { Doctor, VerificationStatus } from "../api/types";
import { Button, ErrorAlert, errorMessage } from "../components/ui";

export default function AdminDoctorsPage() {
  const [filter, setFilter] = useState<VerificationStatus>("unverified");
  const [doctors, setDoctors] = useState<Doctor[] | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    setDoctors(null);
    setError("");
    admin.doctors(filter).then((data) => { if (active) setDoctors(data); })
      .catch((err) => { if (active) setError(errorMessage(err)); });
    return () => { active = false; };
  }, [filter, reload]);

  async function review(doctor: Doctor, decision: "verify" | "reject") {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await admin.review(doctor.user_id, decision);
      setDoctors((prev) => prev?.flatMap((d) => d.user_id !== updated.user_id ? [d]
        : updated.verification_status === filter ? [updated] : []) ?? null);
      setNotice(`${doctor.full_name}: ${decision === "verify" ? "registration verified" : "registration rejected"}.`);
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }

  return (
    <div className="flex flex-col gap-5">
      <div><h1 className="text-2xl font-semibold">Doctor applications</h1>
        <p className="mt-2 max-w-2xl text-slate-600">Check the registration number with the stated medical council before verifying.
          Approval confirms the account; patients must separately consent to record access.</p></div>
      <div><label htmlFor="verification-filter" className="mr-3 text-sm font-medium">Verification status</label>
        <select id="verification-filter" className="min-h-11 rounded-md border border-slate-300 bg-white px-3 py-2 focus-visible:ring-2 focus-visible:ring-teal-600"
          value={filter} disabled={busy} onChange={(e) => { setFilter(e.target.value as VerificationStatus); setNotice(""); }}>
          <option value="unverified">Pending verification</option><option value="verified">Verified</option>
          <option value="rejected">Rejected</option><option value="suspended">Suspended</option>
        </select></div>
      <ErrorAlert>{error}</ErrorAlert>
      {notice && <p role="status" className="rounded-md border border-teal-200 bg-teal-50 p-3 text-teal-900">{notice}</p>}
      {doctors === null && !error && <p>Loading applications…</p>}
      {doctors === null && error && <div><Button variant="secondary" onClick={() => setReload((n) => n + 1)}>Try again</Button></div>}
      {doctors?.length === 0 && <p className="rounded-lg border border-slate-200 bg-white p-6 text-slate-600">No applications with this status.</p>}
      {doctors && doctors.length > 0 && <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table aria-label="Doctor applications" className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-700"><tr>
            <th scope="col" className="p-4">Doctor</th><th scope="col" className="p-4">Registration</th>
            <th scope="col" className="p-4">Practice</th><th scope="col" className="p-4">Review</th>
          </tr></thead>
          <tbody>{doctors.map((doctor) => <tr key={doctor.user_id} className="border-t border-slate-200 align-top">
            <th scope="row" className="p-4 font-medium">{doctor.full_name}</th>
            <td className="p-4"><p className="font-medium">{doctor.registration_number}</p><p className="mt-1 text-slate-600">{doctor.registration_council}</p></td>
            <td className="p-4"><p>{doctor.specialty || "Specialty not provided"}</p><p className="mt-1 text-slate-600">{doctor.clinic_name || "Clinic not provided"}</p></td>
            <td className="p-4"><div className="flex flex-wrap gap-2" role="group" aria-label={`Review ${doctor.full_name}`}>
              {doctor.verification_status !== "verified" && <Button className="min-h-11" disabled={busy} onClick={() => void review(doctor, "verify")}>Verify</Button>}
              {doctor.verification_status !== "rejected" && <Button variant="secondary" className="min-h-11" disabled={busy} onClick={() => void review(doctor, "reject")}>Reject</Button>}
            </div></td>
          </tr>)}</tbody>
        </table>
      </div>}
    </div>
  );
}
