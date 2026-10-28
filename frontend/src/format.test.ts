import { describe, expect, it } from "vitest";
import { formatDate, formatMonth } from "./format";

describe("formatDate", () => {
  it("is day month year, without timezone shift", () => {
    expect(formatDate("2026-03-12")).toBe("12 Mar 2026");
    expect(formatDate("2026-01-01")).toBe("1 Jan 2026");
  });

  it("uses three-letter months on every browser (ICU writes 'Sept' for en-GB)", () => {
    expect(formatDate("2026-09-01")).toBe("1 Sep 2026");
  });

  it("formats a timestamp as month and year for chart ticks", () => {
    expect(formatMonth(new Date(2026, 8, 15).getTime())).toBe("Sep 2026");
  });
});
