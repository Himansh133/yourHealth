import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import EvaluationPage from "./EvaluationPage";

it("labels historical synthetic results and preserves metric denominators", () => {
  render(<EvaluationPage />);
  expect(screen.getByRole("heading", { name: "Evaluation & evidence" })).toBeInTheDocument();
  expect(screen.getByText(/not a measurement of the current build/i)).toBeInTheDocument();
  expect(screen.getByText(/90 questions/)).toBeInTheDocument();
  const row = screen.getByText("Numeric accuracy, value questions (English)").closest("tr")!;
  expect(within(row).getByText("100% (9/9)")).toBeInTheDocument();
  expect(screen.getByText(/not clinical validation/i)).toBeInTheDocument();
});
