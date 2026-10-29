import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi } from "../test/mockApi";
import { renderAt } from "../test/render";
import WhatsAppPage from "./WhatsAppPage";

const ME = { id: "u1", email: "a@example.com", preferred_language: "en" };
const routes = { "/settings/whatsapp": <WhatsAppPage pollMs={10} /> };
const NOT_LINKED = { linked: false, phone: null, linked_at: null };
const LINKED = { linked: true, phone: "+91 ••••••5210", linked_at: "2026-10-29T10:00:00Z" };

describe("WhatsAppPage", () => {
  it("gets a code and shows the exact message to send, with a one-tap link", async () => {
    mockApi({
      "GET /me": ME, "GET /me/whatsapp": NOT_LINKED,
      "POST /me/whatsapp/link-code": { code: "482913", expires_at: "2026-10-29T10:10:00Z", bot_number: "+1 555 0100" },
    });
    const user = renderAt("/settings/whatsapp", routes);

    await user.click(await screen.findByRole("button", { name: "Get a code" }));

    expect(await screen.findByText("LINK 482913")).toBeInTheDocument();
    expect(screen.getByText("+1 555 0100")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open whatsapp/i })).toHaveAttribute(
      "href", "https://wa.me/15550100?text=LINK%20482913");
  });

  it("notices when the phone gets linked", async () => {
    let linked = false;
    mockApi({
      "GET /me": ME, "GET /me/whatsapp": () => (linked ? LINKED : NOT_LINKED),
      "POST /me/whatsapp/link-code": () => { linked = true; return { code: "482913", expires_at: "2026-10-29T10:10:00Z", bot_number: "" }; },
    });
    const user = renderAt("/settings/whatsapp", routes);
    await user.click(await screen.findByRole("button", { name: "Get a code" }));
    expect(await screen.findByText("+91 ••••••5210")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Disconnect" })).toBeInTheDocument();
    expect(screen.queryByText("LINK 482913")).not.toBeInTheDocument();
  });

  it("disconnects", async () => {
    let linked = true;
    const calls = mockApi({
      "GET /me": ME, "GET /me/whatsapp": () => (linked ? LINKED : NOT_LINKED),
      "DELETE /me/whatsapp": () => { linked = false; return { status: 204 }; },
    });
    const user = renderAt("/settings/whatsapp", routes);
    await user.click(await screen.findByRole("button", { name: "Disconnect" }));
    expect(await screen.findByRole("button", { name: "Get a code" })).toBeInTheDocument();
    expect(calls.some((c) => c.method === "DELETE")).toBe(true);
  });

  it("says when the bot number isn't set up", async () => {
    mockApi({
      "GET /me": ME, "GET /me/whatsapp": NOT_LINKED,
      "POST /me/whatsapp/link-code": { code: "482913", expires_at: "2026-10-29T10:10:00Z", bot_number: "" },
    });
    const user = renderAt("/settings/whatsapp", routes);
    await user.click(await screen.findByRole("button", { name: "Get a code" }));
    expect(await screen.findByText(/isn't set up on this server/i)).toBeInTheDocument();
  });
});
