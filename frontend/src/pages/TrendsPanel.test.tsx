import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi } from "../test/mockApi";
import { renderAt } from "../test/render";
import TrendsPanel from "./TrendsPanel";

const ME = { id: "u1", email: "a@example.com", preferred_language: "en" };
const HBA1C = { loinc_code: "4548-4", name: "HbA1c", name_hi: "पिछले 3 महीने की औसत शुगर", unit: "%", category: "diabetes" };

function point(over: Record<string, unknown>) {
  return {
    lab_result_id: "r1", document_id: "d1", page_no: 1, observed_on: "2026-01-10", value: 8.1, qualifier: null,
    range_low: 4, range_high: 5.6, flag: "high", low_confidence: false, ...over,
  };
}

function trend(points: ReturnType<typeof point>[], markers: unknown[] = []) {
  return { test: HBA1C, points, latest: points[points.length - 1], markers };
}

const routes = {
  "/profiles/:pid/trends": <TrendsPanel profileId="p1" />,
  "/documents/:did/review": <p>Source report</p>,
};

describe("TrendsPanel", () => {
  it("shows a card per test with the latest value, unit, date and flag in words", async () => {
    mockApi({
      "GET /me": ME,
      "GET /profiles/p1/trends": [
        trend([point({}), point({ lab_result_id: "r2", document_id: "d2", observed_on: "2026-06-14", value: 7.2 })]),
      ],
    });
    renderAt("/profiles/p1/trends", routes);

    const card = await screen.findByRole("article", { name: "HbA1c" });
    expect(within(card).getByText("पिछले 3 महीने की औसत शुगर")).toBeInTheDocument();
    expect(within(card).getByText("7.2")).toBeInTheDocument();
    expect(within(card).getByText("%")).toBeInTheDocument();
    expect(within(card).getByText(/14 Jun 2026/)).toBeInTheDocument();
    expect(within(card).getByText(/above range/i)).toBeInTheDocument();
  });

  it("offers every point as a table, oldest first, each linked to its source report", async () => {
    mockApi({
      "GET /me": ME,
      "GET /profiles/p1/trends": [
        trend([point({}), point({ lab_result_id: "r2", document_id: "d2", observed_on: "2026-06-14", value: 7.2 })]),
      ],
    });
    const user = renderAt("/profiles/p1/trends", routes);

    await user.click(await screen.findByRole("button", { name: /show values as a table/i }));
    const table = screen.getByRole("table", { name: /hba1c values/i });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows.map((r) => r.textContent)).toEqual([
      expect.stringContaining("10 Jan 2026"),
      expect.stringContaining("14 Jun 2026"),
    ]);
    expect(within(rows[0]).getByText("8.1 %")).toBeInTheDocument();
    expect(within(rows[0]).getByText("4 – 5.6")).toBeInTheDocument();

    await user.click(within(rows[1]).getByRole("link", { name: /14 jun 2026/i }));
    expect(await screen.findByText("Source report")).toBeInTheDocument();
  });

  it("never invents a range: a point without one says so", async () => {
    mockApi({
      "GET /me": ME,
      "GET /profiles/p1/trends": [
        trend([point({}), point({ lab_result_id: "r2", observed_on: "2026-06-14", value: 7.2, range_low: null, range_high: null, flag: "no_range" })]),
      ],
    });
    const user = renderAt("/profiles/p1/trends", routes);
    const card = await screen.findByRole("article", { name: "HbA1c" });
    expect(within(card).getAllByText(/range not printed on this report/i).length).toBeGreaterThan(0);
    await user.click(within(card).getByRole("button", { name: /show values as a table/i }));
    expect(within(card).getByRole("table")).toHaveTextContent("Range not printed on this report");
  });

  it("marks values that haven't been checked yet", async () => {
    mockApi({
      "GET /me": ME,
      "GET /profiles/p1/trends": [
        trend([point({}), point({ lab_result_id: "r2", observed_on: "2026-06-14", value: 72, low_confidence: true })]),
      ],
    });
    const user = renderAt("/profiles/p1/trends", routes);
    const card = await screen.findByRole("article", { name: "HbA1c" });
    expect(within(card).getByText(/latest value not checked yet/i)).toBeInTheDocument();
    await user.click(within(card).getByRole("button", { name: /show values as a table/i }));
    expect(within(card).getByRole("table")).toHaveTextContent("Not checked yet");
  });

  it("says why there are no charts yet", async () => {
    mockApi({ "GET /me": ME, "GET /profiles/p1/trends": [] });
    renderAt("/profiles/p1/trends", routes);
    expect(await screen.findByText(/appear when a test shows up in two or more reports/i)).toBeInTheDocument();
  });

  it("lists medicine start and stop dates linked to the test", async () => {
    mockApi({
      "GET /me": ME,
      "GET /profiles/p1/trends": [
        trend([point({}), point({ lab_result_id: "r2", observed_on: "2026-06-14", value: 7.2 })], [
          { date: "2026-03-01", kind: "start", medicine: "Glycomet 500", ingredient: "metformin", effect_type: "therapeutic" },
          { date: "2026-09-01", kind: "stop", medicine: "Glycomet 500", ingredient: "metformin", effect_type: "therapeutic" },
        ]),
      ],
    });
    renderAt("/profiles/p1/trends", routes);
    const card = await screen.findByRole("article", { name: "HbA1c" });
    expect(within(card).getByText("Glycomet 500 started 1 Mar 2026")).toBeInTheDocument();
    expect(within(card).getByText("Glycomet 500 stopped 1 Sep 2026")).toBeInTheDocument();
  });
});
