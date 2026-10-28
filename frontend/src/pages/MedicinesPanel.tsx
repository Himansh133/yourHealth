import { useEffect, useId, useState, type FormEvent } from "react";
import { medicines as api } from "../api/endpoints";
import type { DrugSearchResult, Frequency, IngredientInfo, Insight, LabEffect, Medicine } from "../api/types";
import { Button, ErrorAlert, errorMessage } from "../components/ui";
import { formatDate } from "../format";

const FREQUENCY: Record<Frequency, string> = {
  OD: "once a day",
  BD: "twice a day",
  TDS: "three times a day",
  QID: "four times a day",
  HS: "at bedtime",
  SOS: "only when needed",
};

const today = () => new Date().toISOString().slice(0, 10);

export default function MedicinesPanel({ profileId, canEdit }: { profileId: string; canEdit: boolean }) {
  const [meds, setMeds] = useState<Medicine[] | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [error, setError] = useState("");

  const reloadInsights = () => api.insights(profileId).then(setInsights).catch(() => {});

  useEffect(() => {
    api.list(profileId).then(setMeds).catch((e) => setError(errorMessage(e)));
    api.insights(profileId).then(setInsights).catch(() => {});
  }, [profileId]);

  function replace(m: Medicine) {
    setMeds((prev) => (prev ?? []).map((x) => (x.id === m.id ? m : x)));
    void reloadInsights();
  }
  function drop(id: string) {
    setMeds((prev) => (prev ?? []).filter((x) => x.id !== id));
    void reloadInsights();
  }

  if (error) return <ErrorAlert>{error}</ErrorAlert>;
  if (!meds) return <p className="text-slate-500">Loading…</p>;

  const pending = meds.filter((m) => !m.confirmed_by_user);
  const current = meds.filter((m) => m.confirmed_by_user);

  return (
    <div className="flex flex-col gap-6">
      <p className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
        This app doesn't suggest, start, stop or change medicines. That depends on things it can't see, so it's your
        doctor's decision. It shows what official drug labels say and what your own reports show.
      </p>

      {pending.length > 0 && (
        <PendingList items={pending} canEdit={canEdit} onConfirmed={replace} onRemoved={drop} />
      )}

      <section aria-labelledby="current-meds" className="flex flex-col gap-3">
        <h2 id="current-meds" className="text-lg font-semibold">Medicines</h2>
        {current.length === 0 && <p className="text-slate-600">No medicines added yet.</p>}
        <div className="grid gap-4 md:grid-cols-2">
          {current.map((m) => (
            <MedicineCard key={m.id} med={m} canEdit={canEdit} onRemoved={() => drop(m.id)} />
          ))}
        </div>
      </section>

      {insights.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-lg font-semibold">What your reports show</h2>
          <ul aria-label="What your reports show" className="flex flex-col gap-2">
            {insights.map((i) => (
              <li key={`${i.medicine_id}-${i.ingredient}-${i.test_name}`}
                className={`rounded-md border bg-white px-3 py-2 text-sm ${i.flagged ? "border-amber-300" : "border-slate-200"}`}>
                {i.flagged && <span className="mr-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-900">Worth discussing</span>}
                {i.message}
              </li>
            ))}
          </ul>
          <p className="text-xs text-slate-500">
            Lab values change for many reasons (food, other medicines, the lab itself). These notes show data, not causes.
          </p>
        </section>
      )}

      {canEdit && <AddMedicineForm profileId={profileId} onAdded={(m) => { setMeds((p) => [...(p ?? []), m]); void reloadInsights(); }} />}
    </div>
  );
}

function PendingList({ items, canEdit, onConfirmed, onRemoved }: {
  items: Medicine[]; canEdit: boolean; onConfirmed: (m: Medicine) => void; onRemoved: (id: string) => void;
}) {
  return (
    <section aria-label="From prescriptions, please confirm" className="flex flex-col gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4">
      <h2 className="font-semibold text-amber-900">From prescriptions: please confirm</h2>
      <p className="text-sm text-amber-900">Nothing is added until you confirm it.</p>
      <ul className="flex flex-col gap-2">
        {items.map((m) => <PendingItem key={m.id} med={m} canEdit={canEdit} onConfirmed={onConfirmed} onRemoved={onRemoved} />)}
      </ul>
    </section>
  );
}

function PendingItem({ med, canEdit, onConfirmed, onRemoved }: {
  med: Medicine; canEdit: boolean; onConfirmed: (m: Medicine) => void; onRemoved: (id: string) => void;
}) {
  const [startedOn, setStartedOn] = useState("");
  const [error, setError] = useState("");
  const dateId = useId();
  const recognised = med.ingredients.length > 0;

  async function confirm() {
    setError("");
    try {
      onConfirmed(await api.update(med.id, { confirmed_by_user: true, ...(startedOn && { started_on: startedOn }) }));
    } catch (e) {
      setError(errorMessage(e));
    }
  }
  async function remove() {
    try {
      await api.remove(med.id);
      onRemoved(med.id);
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  return (
    <li className="flex flex-wrap items-end justify-between gap-3 rounded-md bg-white p-3">
      <div>
        <p className="font-mono text-sm">{med.raw_text}</p>
        <p className="text-sm text-slate-600">
          {recognised ? `${med.name} · ${med.composition ?? med.ingredients.map((i) => i.name).join(" + ")}` :
            "Not recognised. Remove it, or add the medicine below by name."}
        </p>
      </div>
      {canEdit && (
        <div className="flex flex-wrap items-end gap-2">
          {recognised && (
            <>
              <label htmlFor={dateId} className="flex flex-col text-xs text-slate-600">
                Started on
                <input id={dateId} type="date" max={today()} value={startedOn} onChange={(e) => setStartedOn(e.target.value)}
                  className="rounded border border-slate-300 px-2 py-1 text-sm" />
              </label>
              <Button className="!px-3 !py-1 text-sm" onClick={confirm}>Confirm</Button>
            </>
          )}
          <Button variant="secondary" className="!px-3 !py-1 text-sm" onClick={remove}>Remove</Button>
        </div>
      )}
      <ErrorAlert>{error}</ErrorAlert>
    </li>
  );
}

function effectText(e: LabEffect): string {
  const verb = { decrease: "lower", increase: "raise", either: "change" }[e.direction];
  return e.effect_type === "therapeutic"
    ? `${verb.charAt(0).toUpperCase()}${verb.slice(1)}s ${e.test.name} (intended effect)`
    : `May ${verb} ${e.test.name} (doctors watch this)`;
}

function MedicineCard({ med, canEdit, onRemoved }: { med: Medicine; canEdit: boolean; onRemoved: () => void }) {
  const [infos, setInfos] = useState<IngredientInfo[]>([]);
  const titleId = useId();

  useEffect(() => {
    Promise.all(med.ingredients.map((i) => api.ingredient(i.id))).then(setInfos).catch(() => setInfos([]));
  }, [med.ingredients]);

  async function remove() {
    await api.remove(med.id);
    onRemoved();
  }

  return (
    <article aria-labelledby={titleId} className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <header className="flex items-start justify-between gap-2">
        <div>
          <h3 id={titleId} className="text-lg font-semibold">{med.name}</h3>
          {med.ingredients.map((i) => (
            <p key={i.id} className="text-sm text-slate-600">{[i.name, i.drug_class].filter(Boolean).join(" · ")}</p>
          ))}
        </div>
        {canEdit && <Button variant="link" className="text-sm" onClick={remove}>Remove</Button>}
      </header>
      <p className="text-sm text-slate-700">
        {[med.dose_text, med.frequency_code && FREQUENCY[med.frequency_code],
          med.started_on && `since ${formatDate(med.started_on)}`, med.stopped_on && `stopped ${formatDate(med.stopped_on)}`]
          .filter(Boolean).join(" · ")}
      </p>
      {med.ingredients.map((i) => i.used_for && (
        <p key={i.id} className="text-sm text-slate-600">
          <span className="font-medium text-slate-700">From the drug label: </span>{i.used_for}
        </p>
      ))}
      {infos.some((i) => i.effects.length > 0) && (
        <div>
          <h4 className="text-sm font-medium text-slate-700">Lab values it's known to affect</h4>
          <ul className="mt-1 flex flex-col gap-1 text-sm">
            {infos.flatMap((info) => info.effects.map((e) => (
              <li key={`${info.id}-${e.test.loinc_code}`} className="flex flex-wrap gap-x-2">
                <span>{effectText(e)}</span>
                <a href={e.source_url} target="_blank" rel="noopener noreferrer" className="text-teal-700 underline">
                  Drug label
                </a>
              </li>
            )))}
          </ul>
        </div>
      )}
      <p className="text-xs text-slate-500">Discuss any change with your doctor.</p>
    </article>
  );
}

function AddMedicineForm({ profileId, onAdded }: { profileId: string; onAdded: (m: Medicine) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DrugSearchResult[]>([]);
  const [picked, setPicked] = useState<DrugSearchResult | null>(null);
  const [frequency, setFrequency] = useState<Frequency | "">("");
  const [startedOn, setStartedOn] = useState("");
  const [error, setError] = useState("");
  const ids = { input: useId(), list: useId(), freq: useId(), date: useId() };

  useEffect(() => {
    if (picked || query.trim().length < 2) {
      setResults([]);
      return;
    }
    const timer = setTimeout(() => api.search(query).then(setResults).catch(() => setResults([])), 250);
    return () => clearTimeout(timer);
  }, [query, picked]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!picked) return;
    setError("");
    try {
      const added = await api.add(profileId, {
        ...(picked.kind === "brand" ? { brand_id: picked.id } : { ingredient_id: picked.id }),
        ...(frequency && { frequency_code: frequency }),
        ...(startedOn && { started_on: startedOn }),
      });
      onAdded(added);
      setQuery("");
      setPicked(null);
      setFrequency("");
      setStartedOn("");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section className="max-w-xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold">Add a medicine</h2>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div className="relative flex flex-col gap-1">
          <label htmlFor={ids.input} className="text-sm font-medium text-slate-700">Medicine name (brand or generic)</label>
          <input id={ids.input} role="combobox" aria-expanded={results.length > 0} aria-controls={ids.list}
            autoComplete="off" placeholder="Glycomet 500" value={picked ? picked.name : query}
            onChange={(e) => { setPicked(null); setQuery(e.target.value); }}
            className="rounded-md border border-slate-300 px-3 py-2 focus:border-teal-600 focus:outline-none focus:ring-1 focus:ring-teal-600" />
          {results.length > 0 && (
            <ul id={ids.list} role="listbox" className="absolute top-full z-10 mt-1 max-h-64 w-full overflow-auto rounded-md border border-slate-200 bg-white shadow-lg">
              {results.map((r) => (
                <li key={r.id} role="option" aria-selected={false} tabIndex={0}
                  onClick={() => setPicked(r)} onKeyDown={(e) => e.key === "Enter" && setPicked(r)}
                  className="cursor-pointer px-3 py-2 hover:bg-slate-50 focus:bg-slate-100 focus:outline-none">
                  <span className="font-medium">{r.name}</span>
                  <span className="block text-xs text-slate-500">
                    {r.kind === "brand" ? r.composition : `generic${r.drug_class ? ` · ${r.drug_class}` : ""}`}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {picked?.composition && <p className="text-xs text-slate-500">{picked.composition}</p>}
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1">
            <label htmlFor={ids.freq} className="text-sm font-medium text-slate-700">How often (optional)</label>
            <select id={ids.freq} value={frequency} onChange={(e) => setFrequency(e.target.value as Frequency | "")}
              className="rounded-md border border-slate-300 bg-white px-3 py-2">
              <option value="">—</option>
              {Object.entries(FREQUENCY).map(([code, text]) => <option key={code} value={code}>{text} ({code})</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor={ids.date} className="text-sm font-medium text-slate-700">Started on (optional)</label>
            <input id={ids.date} type="date" max={today()} value={startedOn} onChange={(e) => setStartedOn(e.target.value)}
              className="rounded-md border border-slate-300 px-3 py-2" />
          </div>
        </div>
        <p className="text-xs text-slate-500">The start date lets us compare your reports from before and after.</p>
        <ErrorAlert>{error}</ErrorAlert>
        <Button type="submit" disabled={!picked} className="self-start">Add medicine</Button>
      </form>
    </section>
  );
}
