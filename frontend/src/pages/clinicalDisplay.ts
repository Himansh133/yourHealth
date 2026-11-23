import type { LabResult } from "../api/types";

export function printedReading(row: LabResult): string {
  return [row.raw_value, row.raw_unit].filter(Boolean).join(" ");
}

export function changeBetween(before: LabResult, after: LabResult): string | null {
  if (!before.test || !after.test || before.test.loinc_code !== after.test.loinc_code ||
      before.test.unit !== after.test.unit || before.qualifier || after.qualifier ||
      before.value_canonical === null || after.value_canonical === null || before.observed_on >= after.observed_on) return null;
  const delta = after.value_canonical - before.value_canonical;
  if (!Number.isFinite(delta)) return null;
  const unit = after.test.unit === "%" ? "percentage points" : after.test.unit;
  if (delta === 0) return "No numeric change";
  if (Math.abs(delta) < 0.001) return `Change smaller than 0.001 ${unit}`;
  return `${delta > 0 ? "Rose" : "Fell"} by ${Number(Math.abs(delta).toFixed(3))} ${unit}`;
}
