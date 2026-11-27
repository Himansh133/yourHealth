import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import { doctors } from "../api/endpoints";
import { accountHome, useAuth } from "../auth";
import { Button, ErrorAlert, TextField, errorMessage } from "../components/ui";

export default function DoctorRegisterPage() {
  const { user, login, loading } = useAuth();
  const [form, setForm] = useState({ full_name: "", registration_number: "", registration_council: "",
    specialty: "", clinic_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (loading) return <p className="p-6 text-slate-600">Loading…</p>;
  if (user) return <Navigate to={accountHome(user.account_type)} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await doctors.register(form);
      await login(form.email, form.password);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const field = (key: keyof typeof form) => ({ value: form[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => setForm((prev) => ({ ...prev, [key]: e.target.value })) });

  return (
    <main className="mx-auto flex max-w-xl flex-col gap-5 px-4 py-10">
      <Link to="/login" className="text-sm text-teal-700 underline">← Sign in</Link>
      <div>
        <p className="text-sm font-semibold uppercase tracking-wide text-teal-800">HealthSync · For clinicians</p>
        <h1 className="mt-2 text-2xl font-semibold">Doctor registration</h1>
        <p className="mt-2 text-slate-600">An admin will check your registration before approving your account.
          Patient records always require the patient’s permission.</p>
      </div>
      <form onSubmit={submit} className="rounded-lg border border-slate-200 bg-white p-6">
        <fieldset disabled={busy} className="grid gap-4 sm:grid-cols-2">
          <legend className="sr-only">Doctor account details</legend>
          <div className="sm:col-span-2"><TextField label="Full name" required maxLength={200} autoComplete="name" {...field("full_name")} /></div>
          <TextField label="Registration number" required maxLength={200} {...field("registration_number")} />
          <TextField label="Registration council" required maxLength={200} {...field("registration_council")} />
          <TextField label="Specialty (optional)" maxLength={200} {...field("specialty")} />
          <TextField label="Clinic name (optional)" maxLength={200} autoComplete="organization" {...field("clinic_name")} />
          <div className="sm:col-span-2"><TextField label="Email" type="email" required autoComplete="email" {...field("email")} /></div>
          <div className="sm:col-span-2"><TextField label="Password" type="password" required minLength={10} maxLength={128}
            autoComplete="new-password" hint="At least 10 characters." {...field("password")} /></div>
          <div className="sm:col-span-2"><ErrorAlert>{error}</ErrorAlert></div>
          <Button className="min-h-11 sm:col-span-2" type="submit">{busy ? "Submitting…" : "Submit registration"}</Button>
        </fieldset>
      </form>
    </main>
  );
}
