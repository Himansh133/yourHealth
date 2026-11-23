import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import type { ChatAnswer } from "../api/types";
import AnswerInspection from "./AnswerInspection";

it("links medicine and label excerpts to their actual sources", () => {
  const answer: ChatAnswer = { answerable: true, summary: "Medicine information", claims: [], missing_info: [], doctor_note: "", fallback: false, lang: "en", route: ["medicine"],
    retrieved_evidence: [{ id: "E1", text: "medicine | Metformin" }, { id: "E2", text: "drug_info | Metformin" }],
    sources: [{ id: "E1", kind: "medicine", medicine_id: "m1" }, { id: "E2", kind: "drug_label", url: "https://dailymed.nlm.nih.gov/example" }] };
  render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><AnswerInspection answer={answer} profileId="p1" /></MemoryRouter>);
  expect(screen.getByText("Open medicine list")).toHaveAttribute("href", "/profiles/p1/medicines");
  expect(screen.getByText("Open medicine label")).toHaveAttribute("href", "https://dailymed.nlm.nih.gov/example");
});
