import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi } from "../test/mockApi";
import { renderAt } from "../test/render";
import { SHEET } from "../test/sheetFixture";
import PublicSharePage from "./PublicSharePage";

const routes = { "/s/:token": <PublicSharePage /> };

describe("PublicSharePage", () => {
  it("asks for the PIN, then shows the sheet with report links through the share", async () => {
    const calls = mockApi({ "POST /s/tok/unlock": { ok: true }, "GET /s/tok/sheet": SHEET });
    const user = renderAt("/s/tok", routes);

    await user.type(await screen.findByLabelText("PIN"), "4821");
    await user.click(screen.getByRole("button", { name: "Open" }));

    expect(await screen.findByRole("heading", { name: /papa/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /dr lal pathlabs/i })).toHaveAttribute("href", "/api/v1/s/tok/documents/d2");
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ pin: "4821" });
  });

  it("says when the PIN is wrong", async () => {
    mockApi({ "POST /s/tok/unlock": { status: 403, body: { detail: "Wrong PIN" } } });
    const user = renderAt("/s/tok", routes);
    await user.type(await screen.findByLabelText("PIN"), "0000");
    await user.click(screen.getByRole("button", { name: "Open" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Wrong PIN");
  });

  it("says when the link has expired", async () => {
    mockApi({ "POST /s/tok/unlock": { status: 410, body: { detail: "This link has expired or was turned off" } } });
    const user = renderAt("/s/tok", routes);
    await user.type(await screen.findByLabelText("PIN"), "4821");
    await user.click(screen.getByRole("button", { name: "Open" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/expired/);
  });
});
