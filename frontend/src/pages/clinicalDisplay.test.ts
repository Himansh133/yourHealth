import { expect, it } from "vitest";
import { reading } from "../test/clinicalFixtures";
import { changeBetween } from "./clinicalDisplay";

it("does not describe a rounded zero as a numeric rise", () => {
  const before = reading({ observed_on: "2026-01-10", value_canonical: 7.2 });
  const after = reading({ value_canonical: 7.20001 });
  expect(changeBetween(before, after)).toBe("Change smaller than 0.001 percentage points");
});
