import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { monthsAgo } from "../format";
import { mockApi } from "../test/mockApi";
import { renderAt } from "../test/render";
import { SHEET } from "../test/sheetFixture";
import DoctorSheetPanel from "./DoctorSheetPanel";

const ME = { id: "u1", email: "a@example.com", preferred_language: "en" };
const routes = { "/profiles/:pid/sheet": <DoctorSheetPanel profileId="p1" canShare /> };

const SHARE = {
  id: "s1", created_at: "2026-10-29T10:00:00Z", expires_at: "2026-10-30T10:00:00Z", state: "active",
  scope: { from: "2026-05-01", to: "2026-10-29", include_medicines: true }, opens: 2, last_opened_at: "2026-10-29T11:42:00Z",
};

describe("DoctorSheetPanel", () => {
  it("previews the sheet: flagged values with the previous one, medicine flags, trends, medicines, reports", async () => {
    mockApi({ "GET /me": ME, "GET /profiles/p1/sheet": SHEET, "GET /profiles/p1/shares": [] });
    renderAt("/profiles/p1/sheet", routes);

    const flagged = await screen.findByRole("region", { name: "Values outside the report's range" });
    const row = within(flagged).getByText("HbA1c").closest("tr")!;
    expect(within(row).getByText("7.2 %")).toBeInTheDocument();
    expect(within(row).getByText(/high/i)).toBeInTheDocument();
    expect(within(row).getByText(/8\.1 % on 10 Jan 2026/)).toBeInTheDocument();
    expect(screen.getByText(/known to lower vitamin b12/i)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /creatinine trend/i })).toBeInTheDocument();
    expect(screen.getByText("Glycomet 500")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /dr lal pathlabs/i })).toHaveAttribute("href", "/api/v1/documents/d2/file");
  });

  it("asks for a new period and leaving out medicines", async () => {
    const calls = mockApi({ "GET /me": ME, "GET /profiles/p1/sheet": SHEET, "GET /profiles/p1/shares": [] });
    const user = renderAt("/profiles/p1/sheet", routes);
    await screen.findByRole("region", { name: "Values outside the report's range" });

    await user.selectOptions(screen.getByLabelText("Period"), "12");
    await user.click(screen.getByLabelText("Include medicines"));

    const last = calls.filter((c) => c.path === "/profiles/p1/sheet").at(-1)!.url;
    expect(last).toContain(`from=${monthsAgo(12)}`);
    expect(last).toContain("include_medicines=false");
  });

  it("creates a share link and shows the QR and PIN once", async () => {
    const calls = mockApi({
      "GET /me": ME, "GET /profiles/p1/sheet": SHEET, "GET /profiles/p1/shares": [SHARE],
      "POST /profiles/p1/shares": { status: 201, body: { share_id: "s2", url: "http://localhost:5173/s/tok", pin: "4821",
        qr_png_base64: "iVBORw0KGgo=", expires_at: "2026-10-30T10:00:00Z" } },
    });
    const user = renderAt("/profiles/p1/sheet", routes);

    await user.click(await screen.findByRole("radio", { name: "7 days" }));
    await user.click(screen.getByRole("button", { name: "Create share link" }));

    const created = await screen.findByRole("region", { name: "New share link" });
    expect(within(created).getByText("4821")).toBeInTheDocument();
    expect(within(created).getByRole("img", { name: /qr code/i })).toHaveAttribute("src", "data:image/png;base64,iVBORw0KGgo=");
    expect(within(created).getByText("http://localhost:5173/s/tok")).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toMatchObject({ expires_in: "7d", include_medicines: true });
  });

  it("lists past links with how often they were opened and can revoke", async () => {
    const calls = mockApi({
      "GET /me": ME, "GET /profiles/p1/sheet": SHEET, "GET /profiles/p1/shares": [SHARE],
      "POST /shares/s1/revoke": { status: 204 },
    });
    const user = renderAt("/profiles/p1/sheet", routes);

    const item = (await screen.findByText(/opened 2 times/i)).closest("li")!;
    await user.click(within(item).getByRole("button", { name: "Turn off" }));
    expect(calls.some((c) => c.method === "POST" && c.path === "/shares/s1/revoke")).toBe(true);
  });
});
