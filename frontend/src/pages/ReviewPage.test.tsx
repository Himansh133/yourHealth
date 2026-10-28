import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi } from "../test/mockApi";
import { renderAt } from "../test/render";
import ReviewPage from "./ReviewPage";

const ME = { id: "u1", email: "a@example.com", preferred_language: "en" };
const DOC = {
  id: "d1", profile_id: "p1", source_channel: "web", original_filename: "june.pdf", mime_type: "application/pdf",
  size_bytes: 1000, doc_type: "lab_report", lab_name: "Thyrocare", report_date: "2026-06-14", status: "needs_review",
  error_code: null, created_at: "2026-06-15T10:00:00Z",
};
const HBA1C = { loinc_code: "4548-4", name: "HbA1c", name_hi: null, unit: "%", category: "diabetes" };

function row(over: Record<string, unknown>) {
  return {
    id: "r1", document_id: "d1", test: HBA1C, raw_name: "HbA1c", raw_value: "72", raw_unit: "%", raw_range: "4.0 - 5.6",
    printed_flag: null, value_num: 72, value_canonical: 72, qualifier: null, range_low: 4, range_high: 5.6,
    range_low_canonical: 4, range_high_canonical: 5.6, flag: "high", observed_on: "2026-06-14", page_no: 1, bbox: null,
    extraction_confidence: 0.55, verified_by_user: false, ...over,
  };
}

const routes = { "/documents/:did/review": <ReviewPage />, "/profiles/:pid": <p>Profile page</p> };

describe("ReviewPage", () => {
  it("shows the original next to the extracted values and marks doubtful rows", async () => {
    mockApi({
      "GET /me": ME,
      "GET /documents/d1": DOC,
      "GET /profiles/p1/lab-results": [
        row({ id: "r1" }),
        row({ id: "r2", raw_name: "TSH", raw_value: "4.10", raw_unit: "µIU/mL", flag: "normal", extraction_confidence: 0.85 }),
        row({ id: "r3", raw_name: "Creatinine", raw_value: "1.0", extraction_confidence: 0.4, verified_by_user: true }),
      ],
    });
    renderAt("/documents/d1/review", routes);

    expect(await screen.findByTitle(/original report/i)).toHaveAttribute("src", "/api/v1/documents/d1/file");
    const rows = await screen.findAllByRole("row");
    const [, hba1c, tsh, creat] = rows; // first row is the header
    expect(within(hba1c).getByText(/please check/i)).toBeInTheDocument();
    expect(within(hba1c).getByText(/high/i)).toBeInTheDocument();
    expect(within(tsh).queryByText(/please check/i)).not.toBeInTheDocument();
    expect(within(creat).getByText(/checked/i)).toBeInTheDocument();
  });

  it("shows a photo upload as an image", async () => {
    mockApi({ "GET /me": ME, "GET /documents/d1": { ...DOC, mime_type: "image/jpeg" }, "GET /profiles/p1/lab-results": [] });
    renderAt("/documents/d1/review", routes);
    expect(await screen.findByRole("img", { name: /original report/i })).toHaveAttribute("src", "/api/v1/documents/d1/file");
  });

  it("corrects a misread value", async () => {
    const calls = mockApi({
      "GET /me": ME,
      "GET /documents/d1": DOC,
      "GET /profiles/p1/lab-results": [row({})],
      "PATCH /lab-results/r1": row({ raw_value: "7.2", value_num: 7.2, verified_by_user: true }),
    });
    const user = renderAt("/documents/d1/review", routes);

    await user.click(await screen.findByRole("button", { name: /edit hba1c/i }));
    const value = screen.getByLabelText(/^value/i);
    await user.clear(value);
    await user.type(value, "7.2");
    await user.click(screen.getByRole("button", { name: /save/i }));

    const [, hba1c] = await screen.findAllByRole("row");
    expect(await within(hba1c).findByText("7.2")).toBeInTheDocument();
    expect(within(hba1c).getByText(/checked/i)).toBeInTheDocument();
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ raw_value: "7.2" });
  });

  it("confirms a doubtful row as correct without changes", async () => {
    const calls = mockApi({
      "GET /me": ME,
      "GET /documents/d1": DOC,
      "GET /profiles/p1/lab-results": [row({ raw_value: "7.2" })],
      "PATCH /lab-results/r1": row({ raw_value: "7.2", verified_by_user: true }),
    });
    const user = renderAt("/documents/d1/review", routes);
    await user.click(await screen.findByRole("button", { name: /looks right/i }));
    expect(await screen.findByText(/checked/i)).toBeInTheDocument();
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({});
  });

  it("asks for the report date when none was printed, then says all checked", async () => {
    let status = "needs_review";
    const calls = mockApi({
      "GET /me": ME,
      "GET /documents/d1": () => ({ ...DOC, report_date: status === "done" ? "2026-06-14" : null, status }),
      "GET /profiles/p1/lab-results": [row({ extraction_confidence: 0.85 })],
      "PATCH /documents/d1": () => {
        status = "done";
        return { ...DOC, report_date: "2026-06-14", status };
      },
    });
    const user = renderAt("/documents/d1/review", routes);

    expect(await screen.findByText(/date wasn't found/i)).toBeInTheDocument();
    await user.type(screen.getByLabelText(/report date/i), "2026-06-14");
    await user.click(screen.getByRole("button", { name: /save date/i }));

    expect(await screen.findByText(/all values checked/i)).toBeInTheDocument();
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ report_date: "2026-06-14" });
  });

  it("says when the document isn't found", async () => {
    mockApi({ "GET /me": ME });
    renderAt("/documents/nope/review", routes);
    expect(await screen.findByRole("alert")).toHaveTextContent(/not found/i);
  });
});
