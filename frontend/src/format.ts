// Fixed month names: browser locale data differs (ICU writes "Sept" for en-GB), and dates must read the
// same in every browser and match the backend's wording.
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2026-03-12" -> "12 Mar 2026", read as a calendar date (no timezone shift). */
export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

/** Timestamp (ms) -> "Mar 2026", for chart axis ticks. */
export function formatMonth(t: number): string {
  const date = new Date(t);
  return `${MONTHS[date.getMonth()]} ${date.getFullYear()}`;
}
