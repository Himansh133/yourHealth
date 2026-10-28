import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RequireAuth } from "../auth";
import { mockApi } from "../test/mockApi";
import { renderAt } from "../test/render";
import LoginPage from "./LoginPage";

const ME = { id: "u1", email: "a@example.com", preferred_language: "en" };
const routes = {
  "/login": <LoginPage />,
  "/": (
    <RequireAuth>
      <p>Family home</p>
    </RequireAuth>
  ),
};

describe("auth", () => {
  it("sends a logged-out visitor to the login page", async () => {
    mockApi({ "GET /me": { status: 401, body: { detail: "Not logged in" } } });
    renderAt("/", routes);
    expect(await screen.findByRole("heading", { name: /sign in/i })).toBeInTheDocument();
  });

  it("shows the app when the session cookie is valid", async () => {
    mockApi({ "GET /me": ME });
    renderAt("/", routes);
    expect(await screen.findByText("Family home")).toBeInTheDocument();
  });

  it("signs in and goes home", async () => {
    mockApi({
      "GET /me": { status: 401, body: { detail: "Not logged in" } },
      "POST /auth/login": ME,
    });
    const user = renderAt("/login", routes);

    await user.type(await screen.findByLabelText(/email/i), "a@example.com");
    await user.type(screen.getByLabelText(/password/i), "correct horse battery");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("Family home")).toBeInTheDocument();
  });

  it("shows the server's error on a wrong password", async () => {
    mockApi({
      "GET /me": { status: 401, body: { detail: "Not logged in" } },
      "POST /auth/login": { status: 401, body: { detail: "Wrong email or password" } },
    });
    const user = renderAt("/login", routes);

    await user.type(await screen.findByLabelText(/email/i), "a@example.com");
    await user.type(screen.getByLabelText(/password/i), "nope nope nope");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Wrong email or password");
  });

  it("creates an account, then signs in", async () => {
    const calls = mockApi({
      "GET /me": { status: 401, body: { detail: "Not logged in" } },
      "POST /auth/register": { status: 201, body: ME },
      "POST /auth/login": ME,
    });
    const user = renderAt("/login", routes);

    await user.click(await screen.findByRole("button", { name: /create an account/i }));
    expect(screen.getByRole("heading", { name: /create account/i })).toBeInTheDocument();
    await user.type(screen.getByLabelText(/email/i), "a@example.com");
    await user.type(screen.getByLabelText(/password/i), "correct horse battery");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText("Family home")).toBeInTheDocument();
    expect(calls.map((c) => `${c.method} ${c.path}`)).toEqual(
      expect.arrayContaining(["POST /auth/register", "POST /auth/login"]),
    );
  });

  it("tells people the password rule before they submit", async () => {
    mockApi({ "GET /me": { status: 401, body: { detail: "Not logged in" } } });
    const user = renderAt("/login", routes);
    await user.click(await screen.findByRole("button", { name: /create an account/i }));
    expect(screen.getByText(/at least 10 characters/i)).toBeInTheDocument();
  });
});
