import { describe, expect, it } from "vitest";
import { formatDate, formatMonth, monthsAgo } from "./format";

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

describe("monthsAgo", () => {
  it("gives the calendar date n months before, as yyyy-mm-dd", () => {
    expect(monthsAgo(6, new Date(2026, 9, 29))).toBe("2026-04-29");
    expect(monthsAgo(12, new Date(2026, 0, 5))).toBe("2025-01-05");
  });

  it("clamps to the end of a shorter month", () => {
    expect(monthsAgo(1, new Date(2026, 2, 31))).toBe("2026-02-28");
  });
});
