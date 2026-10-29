import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockApi } from "../test/mockApi";
import { renderAt } from "../test/render";
import ChatPanel from "./ChatPanel";

const ME = { id: "u1", email: "a@example.com", preferred_language: "en" };

function answer(over: Record<string, unknown> = {}) {
  return {
    answerable: true,
    summary: "Papa's HbA1c came down from 8.1% to 7.2%.",
    claims: [
      { text: "HbA1c was 8.1% on 10 Jan 2026", evidence_ids: ["E1"] },
      { text: "HbA1c was 7.2% on 14 Jun 2026", evidence_ids: ["E2"] },
    ],
    missing_info: [],
    doctor_note: "Discuss the target HbA1c with his doctor.",
    fallback: false,
    route: ["trend"],
    sources: [
      { id: "E1", kind: "lab_result", lab_result_id: "r1", document_id: "d1", page_no: 1 },
      { id: "E2", kind: "lab_result", lab_result_id: "r2", document_id: "d2", page_no: 2 },
    ],
    ...over,
  };
}

const routes = { "/profiles/:pid/ask": <ChatPanel profileId="p1" profileName="Papa" /> };

describe("ChatPanel", () => {
  it("asks the question and shows the answer with a source link for each claim", async () => {
    const calls = mockApi({ "GET /me": ME, "POST /profiles/p1/chat": answer() });
    const user = renderAt("/profiles/p1/ask", routes);

    await user.type(await screen.findByRole("textbox", { name: /ask about papa's reports/i }), "Is papa's HbA1c improving?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    const reply = await screen.findByRole("article", { name: "Answer" });
    expect(within(reply).getByText("Papa's HbA1c came down from 8.1% to 7.2%.")).toBeInTheDocument();
    const second = within(reply).getByText("HbA1c was 7.2% on 14 Jun 2026").closest("li")!;
    expect(within(second).getByRole("link", { name: /report, page 2/i })).toHaveAttribute("href", "/documents/d2/review");
    expect(within(reply).getByText(/discuss the target hba1c/i)).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ question: "Is papa's HbA1c improving?", lang: "en" });
    expect(screen.getByText("Is papa's HbA1c improving?")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /ask about papa's reports/i })).toHaveValue("");
  });

  it("sends Hindi when Hindi is chosen", async () => {
    const calls = mockApi({ "GET /me": ME, "POST /profiles/p1/chat": answer() });
    const user = renderAt("/profiles/p1/ask", routes);

    await user.click(await screen.findByRole("radio", { name: "हिंदी" }));
    await user.type(screen.getByRole("textbox", { name: /ask about papa's reports/i }), "hba1c kitna hai");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await screen.findByRole("article", { name: "Answer" });
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ question: "hba1c kitna hai", lang: "hi" });
  });

  it("explains when it shows the values instead of a written answer", async () => {
    mockApi({
      "GET /me": ME,
      "POST /profiles/p1/chat": answer({
        fallback: true,
        summary: "I couldn't write a reliable summary; here are the values from your reports.",
        claims: [{ text: "lab_result | HbA1c 7.2 % (ref 4.0-5.6) HIGH | 2026-06-14 | p.2", evidence_ids: ["E2"] }],
        doctor_note: "",
      }),
    });
    const user = renderAt("/profiles/p1/ask", routes);
    await user.type(await screen.findByRole("textbox", { name: /ask about papa's reports/i }), "last hba1c");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    const reply = await screen.findByRole("article", { name: "Answer" });
    expect(within(reply).getByText(/couldn't write a reliable summary/i)).toBeInTheDocument();
    expect(within(reply).getByText(/HbA1c 7.2 %/)).toBeInTheDocument();
    expect(within(reply).queryByText(/for the doctor/i)).not.toBeInTheDocument();
  });

  it("shows what is missing when the reports can't answer", async () => {
    mockApi({
      "GET /me": ME,
      "POST /profiles/p1/chat": answer({
        answerable: false, summary: "I couldn't find this in Papa's reports.", claims: [], sources: [],
        missing_info: ["No lipid profile uploaded"], doctor_note: "",
      }),
    });
    const user = renderAt("/profiles/p1/ask", routes);
    await user.type(await screen.findByRole("textbox", { name: /ask about papa's reports/i }), "cholesterol?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    const reply = await screen.findByRole("article", { name: "Answer" });
    expect(within(reply).getByText("I couldn't find this in Papa's reports.")).toBeInTheDocument();
    expect(within(reply).getByText("No lipid profile uploaded")).toBeInTheDocument();
  });

  it("keeps the question when asking fails", async () => {
    mockApi({ "GET /me": ME, "POST /profiles/p1/chat": { status: 500, body: { detail: "Server error" } } });
    const user = renderAt("/profiles/p1/ask", routes);
    const box = await screen.findByRole("textbox", { name: /ask about papa's reports/i });
    await user.type(box, "last hba1c");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(box).toHaveValue("last hba1c");
  });

  it("can't ask an empty question", async () => {
    mockApi({ "GET /me": ME });
    renderAt("/profiles/p1/ask", routes);
    expect(await screen.findByRole("button", { name: "Ask" })).toBeDisabled();
  });
});
