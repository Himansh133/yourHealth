import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { mockApi } from "../test/mockApi";

const LOGGED_OUT = { status: 401, body: { detail: "Not logged in" } };
beforeEach(() => window.history.replaceState(null, "", "/"));

describe("public introduction", () => {
  it("lets a visitor explore the product without exposing patient records", async () => {
    const calls = mockApi({ "GET /me": LOGGED_OUT });
    render(<App />);
    expect(await screen.findByRole("heading", { name: /every report.*one connected health story/i })).toBeInTheDocument();
    expect(screen.getByText(/illustrative data.*not a real patient/i)).toBeInTheDocument();
    expect(calls.some(c => c.path === "/profiles")).toBe(false);
  });

  it("changes the example record when a different health area is selected", async () => {
    mockApi({ "GET /me": LOGGED_OUT });
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole("button", { name: /kidney health/i }));
    expect(screen.getByRole("button", { name: /kidney health/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText("Example record")).toHaveTextContent("Creatinine");
    expect(screen.getByLabelText("Example record")).toHaveTextContent("mg/dL");
    await user.click(screen.getByRole("button", { name: /pause illustration/i }));
    expect(screen.getByRole("button", { name: /play illustration/i })).toBeInTheDocument();
  });

  it("keeps the sample answer and its evidence together when the question changes", async () => {
    mockApi({ "GET /me": LOGGED_OUT });
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole("button", { name: /where did this answer come from/i }));
    const answer = screen.getByLabelText("Example answer");
    expect(answer).toHaveTextContent(/two example reports/i);
    expect(answer).toHaveTextContent("12 Mar 2026");
    expect(answer).toHaveTextContent("14 Jun 2026");
  });

  it("takes the main call to action directly to account creation", async () => {
    mockApi({ "GET /me": LOGGED_OUT });
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole("link", { name: /get started/i }));
    expect(await screen.findByRole("heading", { name: "Create account" })).toBeInTheDocument();
  });

  it("waits for session discovery before choosing the public or private home", async () => {
    const account = { id: "u1", email: "a@example.com", preferred_language: "en", account_type: "patient" };
    mockApi({ "GET /profiles": [] });
    let finish!: (response: Response) => void;
    vi.mocked(fetch).mockImplementationOnce(() => new Promise<Response>(resolve => { finish = resolve; }));
    render(<App />);
    expect(screen.getByRole("status")).toHaveTextContent(/loading/i);
    expect(screen.queryByRole("heading", { name: /one connected health story/i })).not.toBeInTheDocument();
    await act(async () => finish(new Response(JSON.stringify(account), { headers: { "content-type": "application/json" } })));
    expect(await screen.findByRole("heading", { name: "Family", level: 1 })).toBeInTheDocument();
  });

  it("preserves the family home for an authenticated patient", async () => {
    mockApi({ "GET /me": { id: "u1", email: "a@example.com", preferred_language: "en", account_type: "patient" }, "GET /profiles": [] });
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Family", level: 1 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /one connected health story/i })).not.toBeInTheDocument();
  });
});
