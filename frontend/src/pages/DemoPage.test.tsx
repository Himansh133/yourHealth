import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { documents, profiles } from "../api/endpoints";
import { mockApi } from "../test/mockApi";
import { renderAt } from "../test/render";
import { ME, report } from "../test/clinicalFixtures";
import DemoPage from "./DemoPage";

it("creates a separate synthetic profile and uploads three sample reports", async () => {
  mockApi({ "GET /me": ME });
  const create = vi.spyOn(profiles, "create").mockResolvedValue({ id: "demo", display_name: "Demo · Sample Patient", relation_label: "Synthetic demo data", role: "owner", public_code: "DEMO", birth_year: null, sex: null });
  const upload = vi.spyOn(documents, "upload").mockResolvedValue(report({ profile_id: "demo", status: "queued" }));
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(new Blob(["%PDF-demo"], { type: "application/pdf" }), { headers: { "content-type": "application/pdf" } }));
  const user = renderAt("/demo", { "/demo": <DemoPage />, "/profiles/:pid/reports": <p>Demo reports</p> });
  await user.click(screen.getByRole("button", { name: "Create demo patient" }));
  expect(await screen.findByText("Demo reports")).toBeInTheDocument();
  expect(create).toHaveBeenCalledWith({ display_name: "Demo · Sample Patient", relation_label: "Synthetic demo data" });
  expect(upload).toHaveBeenCalledTimes(3);
  expect(upload.mock.calls.every(([pid]) => pid === "demo")).toBe(true);
});
it("does not create a profile if sample files cannot be loaded", async () => {
  mockApi({ "GET /me": ME });
  const create = vi.spyOn(profiles, "create");
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("Unavailable", { status: 503 }));
  const user = renderAt("/demo", { "/demo": <DemoPage /> });
  await user.click(screen.getByRole("button", { name: "Create demo patient" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/sample reports/i);
  expect(create).not.toHaveBeenCalled();
});
