import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import App from "../App";
import { mockApi } from "../test/mockApi";

const ACCOUNT = { id: "doctor-1", email: "doctor@example.com", preferred_language: "en", account_type: "doctor" };
const DOCTOR = {
  user_id: "doctor-1", full_name: "Dr. Ananya Mehta", registration_number: "DEMO-12345",
  registration_council: "Demo Medical Council", specialty: "General medicine", clinic_name: "Demo clinic",
  verification_status: "unverified", verified_by: null, verified_at: null,
};
const LOGGED_OUT = { status: 401, body: { detail: "Not logged in" } };

beforeEach(() => window.history.replaceState(null, "", "/"));

describe("doctor accounts", () => {
  it("registers a doctor with credentials and opens the pending-verification screen", async () => {
    const calls = mockApi({ "GET /me": LOGGED_OUT, "POST /doctor/register": ACCOUNT,
      "POST /auth/login": ACCOUNT, "GET /doctor/me": DOCTOR });
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole("link", { name: /register as a doctor/i }));
    await user.type(await screen.findByLabelText(/^full name/i), DOCTOR.full_name);
    await user.type(screen.getByLabelText(/^registration number/i), DOCTOR.registration_number);
    await user.type(screen.getByLabelText(/^registration council/i), DOCTOR.registration_council);
    await user.type(screen.getByLabelText(/^specialty/i), DOCTOR.specialty);
    await user.type(screen.getByLabelText(/^clinic name/i), DOCTOR.clinic_name);
    await user.type(screen.getByLabelText(/^email/i), ACCOUNT.email);
    await user.type(screen.getByLabelText(/^password/i), "correct horse battery");
    await user.click(screen.getByRole("button", { name: /submit registration/i }));
    expect(await screen.findByRole("heading", { name: /verification pending/i })).toBeInTheDocument();
    const submission = calls.find((c) => c.path === "/doctor/register");
    expect(submission?.body).toMatchObject({ full_name: "Dr. Ananya Mehta", registration_number: "DEMO-12345",
      registration_council: "Demo Medical Council", specialty: "General medicine", clinic_name: "Demo clinic" });
    expect(screen.queryByRole("link", { name: "WhatsApp" })).not.toBeInTheDocument();
  });

  it("routes an existing doctor to their portal and shows their live verification status", async () => {
    mockApi({ "GET /me": ACCOUNT, "GET /doctor/me": { ...DOCTOR, verification_status: "verified" },
      "GET /doctor/grants": [] });
    render(<App />);
    expect(await screen.findByRole("heading", { name: /registration verified/i })).toBeInTheDocument();
    expect(screen.getByText(/every patient must still approve access/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Request patient access" })).toBeInTheDocument();
    expect(screen.getByText(/no active patient access/i)).toBeInTheDocument();
    expect(screen.queryByText(/add.*family member/i)).not.toBeInTheDocument();
  });

  it("keeps patients out of the doctor portal", async () => {
    window.history.replaceState(null, "", "/doctor");
    const calls = mockApi({ "GET /me": { ...ACCOUNT, account_type: "patient" }, "GET /profiles": [] });
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Family", level: 1 })).toBeInTheDocument();
    expect(calls.some((c) => c.path === "/doctor/me")).toBe(false);
  });

  it("shows a recoverable error if doctor details cannot load", async () => {
    mockApi({ "GET /me": ACCOUNT, "GET /doctor/me": { status: 503, body: { detail: "Temporarily unavailable" } } });
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Temporarily unavailable");
    expect(screen.getByRole("button", { name: /refresh status/i })).toBeInTheDocument();
  });

  it("lets an admin verify an application and removes it from the pending list", async () => {
    let pending = true;
    mockApi({ "GET /me": { ...ACCOUNT, account_type: "admin" },
      "GET /admin/doctors": () => pending ? [DOCTOR] : [],
      "POST /admin/doctors/doctor-1/verify": () => {
        pending = false;
        return { ...DOCTOR, verification_status: "verified" };
      },
    });
    const user = userEvent.setup();
    render(<App />);
    const table = await screen.findByRole("table", { name: /doctor applications/i });
    expect(within(table).getByText("DEMO-12345")).toBeInTheDocument();
    await user.click(within(table).getByRole("button", { name: /verify/i }));
    expect(await screen.findByRole("status")).toHaveTextContent(/verified/i);
    expect(await screen.findByText(/no.*applications/i)).toBeInTheDocument();
  });

  it("preserves an application and reports failed admin decisions", async () => {
    mockApi({ "GET /me": { ...ACCOUNT, account_type: "admin" }, "GET /admin/doctors": [DOCTOR],
      "POST /admin/doctors/doctor-1/reject": { status: 503, body: { detail: "Review could not be saved" } } });
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole("button", { name: /reject/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Review could not be saved");
    expect(screen.getByText("DEMO-12345")).toBeInTheDocument();
  });
});
