import { screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { mockApi } from "../test/mockApi";
import { renderAt } from "../test/render";
import { ME, reading, report } from "../test/clinicalFixtures";
import OverviewPanel from "./OverviewPanel";

const routes = { "/": <OverviewPanel profileId="p1" profileName="Papa" /> };
it("summarizes dated reports and sourced recent readings without claiming improvement", async () => {
  mockApi({ "GET /me": ME, "GET /profiles/p1/documents": [report(), report({ id: "d1", report_date: "2026-01-10", status: "needs_review" })],
    "GET /profiles/p1/lab-results": [reading(), reading({ id: "r1", document_id: "d1", observed_on: "2026-01-10", value_canonical: 8.1, raw_value: "8.1" })] });
  renderAt("/", routes);
  expect(await screen.findByRole("heading", { name: "At a glance" })).toBeInTheDocument();
  expect(await screen.findByText(/Fell by 0.9 percentage points/)).toBeInTheDocument();
  expect(screen.getAllByText("14 Jun 2026").length).toBeGreaterThan(0);
  expect(screen.getByRole("link", { name: /review report/i })).toHaveAttribute("href", "/documents/d1/review");
  expect(screen.getAllByText("Not checked yet").length).toBeGreaterThan(0);
  expect(screen.queryByText(/improved/i)).not.toBeInTheDocument();
});
it("offers an upload path for an empty profile", async () => {
  mockApi({ "GET /me": ME, "GET /profiles/p1/documents": [], "GET /profiles/p1/lab-results": [] });
  renderAt("/", routes);
  expect(await screen.findByText(/no reports yet for papa/i)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Upload a report" })).toHaveAttribute("href", "/profiles/p1/reports");
});
it("shows errors instead of misleading empty totals", async () => {
  mockApi({ "GET /me": ME, "GET /profiles/p1/documents": [], "GET /profiles/p1/lab-results": { status: 500, body: { detail: "Unavailable" } } });
  renderAt("/", routes);
  expect(await screen.findByRole("alert")).toHaveTextContent("Unavailable");
  expect(screen.queryByText(/no reports yet/i)).not.toBeInTheDocument();
});
it("does not compare duplicate dates or qualified readings", async () => {
  mockApi({ "GET /me": ME, "GET /profiles/p1/documents": [report()], "GET /profiles/p1/lab-results": [
    reading({ qualifier: ">" }), reading({ id: "old", observed_on: "2026-01-10" }), reading({ id: "duplicate", observed_on: "2026-01-10" }),
  ] });
  renderAt("/", routes);
  expect(await screen.findByText(/not enough unambiguous/i)).toBeInTheDocument();
  expect(screen.queryByText(/fell by/i)).not.toBeInTheDocument();
});
it("does not use upload-date fallbacks as report dates for a trend", async () => {
  mockApi({ "GET /me": ME, "GET /profiles/p1/documents": [report({ report_date: null }), report({ id: "d1", report_date: "2026-01-10" })],
    "GET /profiles/p1/lab-results": [reading(), reading({ id: "r1", document_id: "d1", observed_on: "2026-01-10", value_canonical: 8.1 })] });
  renderAt("/", routes);
  expect(await screen.findByText(/not enough unambiguous/i)).toBeInTheDocument();
});
