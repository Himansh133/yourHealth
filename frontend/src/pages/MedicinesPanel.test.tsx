import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi } from "../test/mockApi";
import { renderAt } from "../test/render";
import MedicinesPanel from "./MedicinesPanel";

const ME = { id: "u1", email: "a@example.com", preferred_language: "en" };
const METFORMIN = { id: "i1", name: "metformin", drug_class: "biguanide", used_for: "Metformin is indicated as an adjunct to diet and exercise to improve glycemic control in adults with type 2 diabetes mellitus." };
const HBA1C = { loinc_code: "4548-4", name: "HbA1c", name_hi: null, unit: "%", category: "diabetes" };
const B12 = { loinc_code: "2132-9", name: "Vitamin B12", name_hi: null, unit: "pg/mL", category: "vitamin" };

function med(over: Record<string, unknown>) {
  return {
    id: "m1", name: "Glycomet 500", brand_id: "b1", composition: "Metformin (500mg)", ingredients: [METFORMIN],
    raw_text: "Glycomet 500", dose_text: null, frequency_code: "BD", started_on: "2026-03-01", stopped_on: null,
    confirmed_by_user: true, source_document_id: null, ...over,
  };
}

const METFORMIN_INFO = {
  ...METFORMIN, atc_code: "A10BA02", label_url: "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=x",
  effects: [
    { test: HBA1C, direction: "decrease", effect_type: "therapeutic", typical_onset: "about 3 months",
      note_en: "Metformin is used to lower blood sugar.", source_name: "openFDA label: metformin",
      source_section: "indications_and_usage", source_url: "https://dailymed.nlm.nih.gov/x", reviewed_by: null },
    { test: B12, direction: "decrease", effect_type: "monitor", typical_onset: "months to years",
      note_en: "Long-term metformin use can lower vitamin B12.", source_name: "openFDA label: metformin",
      source_section: "warnings_and_cautions", source_url: "https://dailymed.nlm.nih.gov/x", reviewed_by: null },
  ],
};

const base = {
  "GET /me": ME,
  "GET /drugs/ingredients/i1": METFORMIN_INFO,
  "GET /profiles/p1/medicine-insights": [],
};

const routes = { "/profiles/:pid/medicines": <MedicinesPanel profileId="p1" canEdit /> };

describe("MedicinesPanel", () => {
  it("shows each medicine with its generic name, what it's for, and label-sourced lab links", async () => {
    mockApi({ ...base, "GET /profiles/p1/medicines": [med({})] });
    renderAt("/profiles/p1/medicines", routes);

    const card = await screen.findByRole("article", { name: "Glycomet 500" });
    expect(within(card).getByText(/metformin · biguanide/i)).toBeInTheDocument();
    expect(within(card).getByText(/twice a day/i)).toBeInTheDocument();
    expect(within(card).getByText(/since 1 Mar 2026/i)).toBeInTheDocument();
    expect(within(card).getByText(/improve glycemic control/i)).toBeInTheDocument();
    expect(await within(card).findByText(/lowers hba1c \(intended effect\)/i)).toBeInTheDocument();
    expect(within(card).getByText(/may lower vitamin b12 \(doctors watch this\)/i)).toBeInTheDocument();
    expect(within(card).getAllByRole("link", { name: /drug label/i })[0]).toHaveAttribute(
      "href", "https://dailymed.nlm.nih.gov/x");
    expect(within(card).getByText(/discuss any change with your doctor/i)).toBeInTheDocument();
  });

  it("states that choosing medicines is the doctor's decision", async () => {
    mockApi({ ...base, "GET /profiles/p1/medicines": [] });
    renderAt("/profiles/p1/medicines", routes);
    expect(await screen.findByText(/doesn't suggest, start, stop or change medicines/i)).toBeInTheDocument();
  });

  it("shows insights, with the ones worth discussing marked", async () => {
    mockApi({
      ...base,
      "GET /profiles/p1/medicines": [med({})],
      "GET /profiles/p1/medicine-insights": [
        { medicine_id: "m1", medicine_name: "Glycomet 500", ingredient: "metformin", test_name: "HbA1c",
          status: "matches_expected", flagged: false, message: "HbA1c went from 8.1 % to 7.2 %. This matches the expected effect of metformin.",
          source_url: "https://dailymed.nlm.nih.gov/x", source_section: "indications_and_usage" },
        { medicine_id: "m1", medicine_name: "Glycomet 500", ingredient: "metformin", test_name: "Vitamin B12",
          status: "watch", flagged: true, message: "Metformin is known to lower Vitamin B12 over time. Worth mentioning to your doctor.",
          source_url: "https://dailymed.nlm.nih.gov/x", source_section: "warnings_and_cautions" },
      ],
    });
    renderAt("/profiles/p1/medicines", routes);

    const list = await screen.findByRole("list", { name: /what your reports show/i });
    const items = within(list).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("matches the expected effect");
    expect(within(items[0]).queryByText(/worth discussing/i)).not.toBeInTheDocument();
    expect(within(items[1]).getByText(/worth discussing/i)).toBeInTheDocument();
  });

  it("confirms a medicine read from a prescription, with its start date", async () => {
    const calls = mockApi({
      ...base,
      "GET /profiles/p1/medicines": [med({ confirmed_by_user: false, started_on: null, raw_text: "1. Tab Glycomet 500 1-0-1", source_document_id: "d1" })],
      "PATCH /medicines/m1": med({}),
    });
    const user = renderAt("/profiles/p1/medicines", routes);

    const pending = await screen.findByRole("region", { name: /from prescriptions/i });
    expect(within(pending).getByText("1. Tab Glycomet 500 1-0-1")).toBeInTheDocument();
    await user.type(within(pending).getByLabelText(/started on/i), "2026-03-01");
    await user.click(within(pending).getByRole("button", { name: /confirm/i }));

    expect(await screen.findByRole("article", { name: "Glycomet 500" })).toBeInTheDocument();
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ confirmed_by_user: true, started_on: "2026-03-01" });
  });

  it("removes a wrongly read prescription line", async () => {
    const calls = mockApi({
      ...base,
      "GET /profiles/p1/medicines": [med({ id: "m9", confirmed_by_user: false, brand_id: null, ingredients: [], name: "3. Tab Paracip 500 SOS", raw_text: "3. Tab Paracip 500 SOS" })],
      "DELETE /medicines/m9": { status: 204 },
    });
    const user = renderAt("/profiles/p1/medicines", routes);
    const pending = await screen.findByRole("region", { name: /from prescriptions/i });
    expect(within(pending).getByText(/not recognised/i)).toBeInTheDocument();
    await user.click(within(pending).getByRole("button", { name: /remove/i }));
    expect(await screen.findByText(/no medicines added yet/i)).toBeInTheDocument();
    expect(calls.some((c) => c.method === "DELETE" && c.path === "/medicines/m9")).toBe(true);
  });

  it("adds a medicine by searching for the brand", async () => {
    const calls = mockApi({
      ...base,
      "GET /profiles/p1/medicines": [],
      "GET /drugs/search": [{ kind: "brand", id: "b7", name: "Telma 40", composition: "Telmisartan (40mg)",
                               ingredients: [], drug_class: null }],
      "POST /profiles/p1/medicines": { status: 201, body: med({ id: "m7", name: "Telma 40", ingredients: [] }) },
    });
    const user = renderAt("/profiles/p1/medicines", routes);

    await user.type(await screen.findByLabelText(/medicine name/i), "telma");
    await user.click(await screen.findByRole("option", { name: /telma 40/i }));
    await user.selectOptions(screen.getByLabelText(/how often/i), "OD");
    await user.type(screen.getByLabelText(/^started on/i), "2026-01-15");
    await user.click(screen.getByRole("button", { name: /add medicine/i }));

    expect(await screen.findByRole("article", { name: "Telma 40" })).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({
      brand_id: "b7", frequency_code: "OD", started_on: "2026-01-15" });
  });

  it("hides editing for viewers", async () => {
    mockApi({ ...base, "GET /profiles/p1/medicines": [med({})] });
    renderAt("/profiles/p1/medicines", { "/profiles/:pid/medicines": <MedicinesPanel profileId="p1" canEdit={false} /> });
    await screen.findByRole("article", { name: "Glycomet 500" });
    expect(screen.queryByLabelText(/medicine name/i)).not.toBeInTheDocument();
  });
});
