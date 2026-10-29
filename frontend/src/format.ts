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

/** Local calendar date n months before `today`, as "yyyy-mm-dd" (31 Mar minus 1 month is 28 Feb). */
export function monthsAgo(n: number, today = new Date()): string {
  const target = new Date(today.getFullYear(), today.getMonth() - n, 1);
  const lastDay = new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate();
  target.setDate(Math.min(today.getDate(), lastDay));
  const pad = (x: number) => String(x).padStart(2, "0");
  return `${target.getFullYear()}-${pad(target.getMonth() + 1)}-${pad(target.getDate())}`;
}
