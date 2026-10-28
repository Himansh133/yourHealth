import { useEffect, useId, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { profiles as profilesApi } from "../api/endpoints";
import type { Profile, Sex } from "../api/types";
import { Button, ErrorAlert, TextField, errorMessage } from "../components/ui";

export default function FamilyPage() {
  const [profiles, setProfiles] = useState<Profile[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    profilesApi.list().then(setProfiles).catch((e) => setError(errorMessage(e)));
  }, []);

  return (
    <div className="flex flex-col gap-8">
      <section>
        <h1 className="mb-4 text-2xl font-semibold">Family</h1>
        <ErrorAlert>{error}</ErrorAlert>
        {profiles === null && !error && <p className="text-slate-500">Loading…</p>}
        {profiles?.length === 0 && (
          <p className="text-slate-600">Add yourself and your family below. Every report belongs to one person.</p>
        )}
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {profiles?.map((p) => (
            <li key={p.id}>
              <Link
                to={`/profiles/${p.id}`}
                className="block rounded-lg border border-slate-200 bg-white p-4 shadow-sm hover:border-teal-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-600"
              >
                <span className="block text-lg font-medium">{p.display_name}</span>
                <span className="text-sm capitalize text-slate-500">
                  {[p.relation_label, p.birth_year && `born ${p.birth_year}`].filter(Boolean).join(" · ") || " "}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
      <AddProfileForm onAdded={(p) => setProfiles((prev) => [...(prev ?? []), p])} />
    </div>
  );
}

function AddProfileForm({ onAdded }: { onAdded: (p: Profile) => void }) {
  const [name, setName] = useState("");
  const [relation, setRelation] = useState("");
  const [birthYear, setBirthYear] = useState("");
  const [sex, setSex] = useState<Sex | "">("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const sexId = useId();

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const created = await profilesApi.create({
        display_name: name.trim(),
        ...(relation.trim() && { relation_label: relation.trim() }),
        ...(birthYear && { birth_year: Number(birthYear) }),
        ...(sex && { sex }),
      });
      onAdded(created);
      setName("");
      setRelation("");
      setBirthYear("");
      setSex("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="max-w-xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold">Add a family member</h2>
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <TextField label="Name" required maxLength={60} placeholder="Papa" value={name}
          onChange={(e) => setName(e.target.value)} />
        <TextField label="Relation (optional)" maxLength={40} placeholder="father" value={relation}
          onChange={(e) => setRelation(e.target.value)} />
        <TextField label="Year of birth (optional)" type="number" inputMode="numeric" min={1900}
          max={new Date().getFullYear()} value={birthYear} onChange={(e) => setBirthYear(e.target.value)} />
        <div className="flex flex-col gap-1">
          <label htmlFor={sexId} className="text-sm font-medium text-slate-700">Sex (optional)</label>
          <select id={sexId} value={sex} onChange={(e) => setSex(e.target.value as Sex | "")}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600">
            <option value="">—</option>
            <option value="female">Female</option>
            <option value="male">Male</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div className="sm:col-span-2 flex flex-col gap-3">
          <ErrorAlert>{error}</ErrorAlert>
          <Button type="submit" disabled={busy} className="self-start">{busy ? "Adding…" : "Add"}</Button>
        </div>
      </form>
    </section>
  );
}
