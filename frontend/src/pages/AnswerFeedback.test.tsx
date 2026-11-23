import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { mockApi } from "../test/mockApi";
import AnswerFeedback from "./AnswerFeedback";

it("saves feedback with the answer id and confirms the selected category", async () => {
  const calls = mockApi({ "PUT /profiles/p1/chat/a1/feedback": { answer_id: "a1", category: "too_long" } });
  render(<AnswerFeedback profileId="p1" answerId="a1" />);
  await userEvent.click(screen.getByRole("button", { name: "Too long" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Feedback saved");
  expect(screen.getByRole("button", { name: "Too long" })).toHaveAttribute("aria-pressed", "true");
  expect(calls[0].body).toEqual({ category: "too_long" });
});
it("keeps feedback retryable when saving fails", async () => {
  mockApi({ "PUT /profiles/p1/chat/a1/feedback": { status: 500, body: { detail: "Could not save" } } });
  render(<AnswerFeedback profileId="p1" answerId="a1" />);
  await userEvent.click(screen.getByRole("button", { name: "Wrong evidence" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Could not save");
  expect(screen.getByRole("button", { name: "Wrong evidence" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "Wrong evidence" })).toHaveAttribute("aria-pressed", "false");
});
