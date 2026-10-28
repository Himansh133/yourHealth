import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RequireAuth } from "../auth";
import Layout from "../components/Layout";
import { mockApi } from "../test/mockApi";
import { renderAt } from "../test/render";
import FamilyPage from "./FamilyPage";

const ME = { id: "u1", email: "a@example.com", preferred_language: "en" };
const PAPA = { id: "p1", display_name: "Papa", birth_year: 1968, sex: "male", role: "owner", relation_label: "father" };

const routes = {
  "/": (
    <RequireAuth>
      <Layout>
        <FamilyPage />
      </Layout>
    </RequireAuth>
  ),
  "/login": <p>Login page</p>,
  "/profiles/:pid": <p>Profile page</p>,
};

describe("FamilyPage", () => {
  it("lists family members with their relation and links to each", async () => {
    mockApi({ "GET /me": ME, "GET /profiles": [PAPA] });
    const user = renderAt("/", routes);

    const card = await screen.findByRole("link", { name: /papa/i });
    expect(within(card).getByText(/father/i)).toBeInTheDocument();
    await user.click(card);
    expect(await screen.findByText("Profile page")).toBeInTheDocument();
  });

  it("explains what to do when there are no profiles yet", async () => {
    mockApi({ "GET /me": ME, "GET /profiles": [] });
    renderAt("/", routes);
    expect(await screen.findByText(/add yourself and your family/i)).toBeInTheDocument();
  });

  it("adds a family member", async () => {
    const created = { ...PAPA, id: "p2", display_name: "Mummy", relation_label: "mother", sex: "female", birth_year: 1971 };
    const calls = mockApi({ "GET /me": ME, "GET /profiles": [], "POST /profiles": { status: 201, body: created } });
    const user = renderAt("/", routes);

    await user.type(await screen.findByLabelText(/^name/i), "Mummy");
    await user.type(screen.getByLabelText(/relation/i), "mother");
    await user.type(screen.getByLabelText(/year of birth/i), "1971");
    await user.selectOptions(screen.getByLabelText(/sex/i), "female");
    await user.click(screen.getByRole("button", { name: /add/i }));

    expect(await screen.findByRole("link", { name: /mummy/i })).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({
      display_name: "Mummy",
      relation_label: "mother",
      birth_year: 1971,
      sex: "female",
    });
  });

  it("shows the server error if adding fails", async () => {
    mockApi({
      "GET /me": ME,
      "GET /profiles": [],
      "POST /profiles": { status: 422, body: { detail: [{ loc: ["body", "birth_year"], msg: "too old" }] } },
    });
    const user = renderAt("/", routes);
    await user.type(await screen.findByLabelText(/^name/i), "Dadi");
    await user.click(screen.getByRole("button", { name: /add/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("birth_year: too old");
  });

  it("signs out from the header", async () => {
    mockApi({ "GET /me": ME, "GET /profiles": [], "POST /auth/logout": { status: 204 } });
    const user = renderAt("/", routes);
    await user.click(await screen.findByRole("button", { name: /sign out/i }));
    expect(await screen.findByText("Login page")).toBeInTheDocument();
  });
});
