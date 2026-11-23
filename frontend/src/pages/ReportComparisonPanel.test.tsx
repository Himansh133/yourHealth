import { screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { labs } from "../api/endpoints";
import type { LabResult } from "../api/types";
import { mockApi } from "../test/mockApi";
import { renderAt } from "../test/render";
import { ME, reading, report } from "../test/clinicalFixtures";
import ReportComparisonPanel from "./ReportComparisonPanel";

function setup(before: LabResult[], after: LabResult[]) {
  mockApi({ "GET /me": ME, "GET /profiles/p1/documents": [report(), report({ id: "d1", report_date: "2026-01-10" })] });
  vi.spyOn(labs, "forDocument").mockImplementation(async (_, did) => did === "d1" ? before : after);
  return renderAt("/", { "/": <ReportComparisonPanel profileId="p1" /> });
}
it("compares matching tests with dated sources and verification labels", async () => {
  setup([reading({ id: "r1", document_id: "d1", observed_on: "2026-01-10", raw_value: "8.1", value_canonical: 8.1 })], [reading()]);
  expect(await screen.findByText("Fell by 0.9 percentage points")).toBeInTheDocument();
  expect(screen.getByLabelText("Earlier report")).toHaveValue("d1");
  expect(screen.getByLabelText("Later report")).toHaveValue("d2");
  expect(screen.getAllByText("Not checked yet")).toHaveLength(2);
  const table = screen.getByRole("table");
  expect(within(table).getByRole("link", { name: /8.1 %/ })).toHaveAttribute("href", "/documents/d1/review");
});
it("does not calculate differences for qualified, incompatible or duplicate readings", async () => {
  setup([reading({ document_id: "d1", observed_on: "2026-01-10" }), reading({ id: "duplicate", document_id: "d1", observed_on: "2026-01-10" })], [reading({ qualifier: ">" })]);
  expect(await screen.findByText("Multiple readings; review the report")).toBeInTheDocument();
  expect(screen.getByText("Not comparable")).toBeInTheDocument();
  expect(screen.queryByText(/fell by|rose by/i)).not.toBeInTheDocument();
});
it("shows missing tests without treating absence as zero", async () => {
  setup([], [reading()]);
  expect(await screen.findByText("Not in this report")).toBeInTheDocument();
  expect(screen.getByText("Not comparable")).toBeInTheDocument();
});
it("does not compare raw numbers when canonical units are unavailable", async () => {
  setup([reading({ document_id: "d1", observed_on: "2026-01-10", value_canonical: null, raw_unit: "mmol/mol" })], [reading()]);
  expect(await screen.findByText("Not comparable")).toBeInTheDocument();
});
it("explains when fewer than two reports are available", async () => {
  mockApi({ "GET /me": ME, "GET /profiles/p1/documents": [report()] });
  renderAt("/", { "/": <ReportComparisonPanel profileId="p1" /> });
  expect(await screen.findByText(/upload at least two/i)).toBeInTheDocument();
});
