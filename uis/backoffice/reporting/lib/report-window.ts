/** First day of (current calendar month − 11) through now (ISO UTC). */

export const reportWindowIso = (now = new Date()): { start: string; end: string } => {
  const end = new Date(now);
  const start = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth() - 11, 1));
  return { start: start.toISOString(), end: end.toISOString() };
};

export const monthKey = (isoDate: string): string => isoDate.slice(0, 7);

export const filterByMonth = <T extends { date: string }>(
  rows: T[],
  month: string,
): T[] => rows.filter((row) => monthKey(row.date) === month);

export const lastTwelveMonthKeys = (now = new Date()): string[] => {
  const months: string[] = [];
  for (let i = 11; i >= 0; i -= 1) {
    const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - i, 1));
    const m = String(d.getUTCMonth() + 1).padStart(2, "0");
    months.push(`${d.getUTCFullYear()}-${m}`);
  }
  return months;
};
