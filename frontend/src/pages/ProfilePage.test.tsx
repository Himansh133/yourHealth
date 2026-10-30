import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi } from "../test/mockApi";
import { renderAt } from "../test/render";
import ProfilePage from "./ProfilePage";

const ME = { id: "u1", email: "a@example.com", preferred_language: "en" };
const PAPA = { id: "p1", display_name: "Papa", birth_year: 1968, sex: "male", role: "owner", relation_label: "father" };

function doc(over: Record<string, unknown>) {
  return {
    id: "d1", profile_id: "p1", source_channel: "web", original_filename: "report.pdf", mime_type: "application/pdf",
    size_bytes: 1000, doc_type: "lab_report", lab_name: "Thyrocare", report_date: "2026-03-12", status: "done",
    error_code: null, created_at: "2026-03-13T10:00:00Z", ...over,
  };
}

const routes = {
  "/profiles/:pid": <ProfilePage pollMs={20} />,
  "/documents/:did/review": <p>Review page</p>,
  "/profiles/:pid/medicines": <p>Medicines tab</p>,
};

describe("ProfilePage reports", () => {
  it("shows the profile name and each report with a friendly status", async () => {
    mockApi({
      "GET /me": ME,
      "GET /profiles": [PAPA],
      "GET /profiles/p1/documents": [
        doc({ id: "d1", status: "done" }),
        doc({ id: "d2", status: "needs_review", original_filename: "june.pdf" }),
        doc({ id: "d3", status: "failed", error_code: "ocr_unavailable", original_filename: "photo.jpg" }),
      ],
    });
    renderAt("/profiles/p1", routes);

    expect(await screen.findByRole("heading", { name: "Papa" })).toBeInTheDocument();
    const rows = await screen.findAllByRole("listitem");
    expect(within(rows[0]).getByText(/thyrocare/i)).toBeInTheDocument();
    expect(within(rows[0]).getByText(/12 Mar 2026/)).toBeInTheDocument();
    expect(within(rows[1]).getByText(/please check/i)).toBeInTheDocument();
    expect(within(rows[2]).getByText(/couldn't read/i)).toBeInTheDocument();
  });

  it("links a report that needs checking to the review screen", async () => {
    mockApi({
      "GET /me": ME,
      "GET /profiles": [PAPA],
      "GET /profiles/p1/documents": [doc({ id: "d2", status: "needs_review" })],
    });
    const user = renderAt("/profiles/p1", routes);
    await user.click(await screen.findByRole("link", { name: /check values/i }));
    expect(await screen.findByText("Review page")).toBeInTheDocument();
  });

  it("uploads a file and shows it while it is being read", async () => {
    const calls = mockApi({
      "GET /me": ME,
      "GET /profiles": [PAPA],
      "GET /profiles/p1/documents": [],
      "POST /profiles/p1/documents": { status: 201, body: doc({ id: "new", status: "queued", report_date: null, lab_name: null }) },
      "GET /documents/new": doc({ id: "new", status: "extracting", report_date: null, lab_name: null }),
    });
    const user = renderAt("/profiles/p1", routes);

    const file = new File(["%PDF-1.7"], "report.pdf", { type: "application/pdf" });
    await user.upload(await screen.findByLabelText(/upload a report/i), file);

    expect(await screen.findByText(/reading/i)).toBeInTheDocument();
    const post = calls.find((c) => c.method === "POST")!;
    expect((post.body as FormData).get("file")).toBe(file);
  });

  it("keeps checking until processing finishes", async () => {
    let polls = 0;
    mockApi({
      "GET /me": ME,
      "GET /profiles": [PAPA],
      "GET /profiles/p1/documents": [doc({ id: "d1", status: "queued" })],
      "GET /documents/d1": () => (++polls < 2 ? doc({ id: "d1", status: "parsing" }) : doc({ id: "d1", status: "done" })),
    });
    renderAt("/profiles/p1", routes);
    expect(await screen.findByText(/done/i, {}, { timeout: 2000 })).toBeInTheDocument();
  });

  it("shows why an upload was rejected", async () => {
    mockApi({
      "GET /me": ME,
      "GET /profiles": [PAPA],
      "GET /profiles/p1/documents": [],
      "POST /profiles/p1/documents": {
        status: 422,
        body: { detail: { code: "pdf_encrypted", message: "This PDF is password-protected." } },
      },
    });
    const user = renderAt("/profiles/p1", routes);
    await user.upload(await screen.findByLabelText(/upload a report/i), new File(["x"], "locked.pdf", { type: "application/pdf" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("password-protected");
  });

  it("says when the profile doesn't exist or isn't yours", async () => {
    mockApi({ "GET /me": ME, "GET /profiles": [PAPA] });
    renderAt("/profiles/someone-else", routes);
    expect(await screen.findByText(/not found/i)).toBeInTheDocument();
  });

  it("sends a processed prescription to the medicines tab to confirm", async () => {
    mockApi({
      "GET /me": ME,
      "GET /profiles": [PAPA],
      "GET /profiles/p1/documents": [doc({ id: "d5", doc_type: "prescription", lab_name: null, report_date: null })],
    });
    const user = renderAt("/profiles/p1", routes);
    await user.click(await screen.findByRole("link", { name: /confirm medicines/i }));
    expect(await screen.findByText("Medicines tab")).toBeInTheDocument();
  });
});

describe("ProfilePage tabs", () => {
  it("names every section, with the short sheet label still read as Doctor sheet", async () => {
    mockApi({ "GET /me": ME, "GET /profiles": [PAPA], "GET /profiles/p1/documents": [] });
    renderAt("/profiles/p1", routes);

    const nav = await screen.findByRole("navigation", { name: "Profile sections" });
    const names = within(nav).getAllByRole("link").map((a) => a.getAttribute("aria-label") ?? a.textContent);
    expect(names).toEqual(["Reports", "Trends", "Medicines", "Ask", "Doctor sheet"]);
    expect(within(nav).getByRole("link", { name: "Doctor sheet" })).toHaveAttribute("href", "/profiles/p1/sheet");
  });
});
