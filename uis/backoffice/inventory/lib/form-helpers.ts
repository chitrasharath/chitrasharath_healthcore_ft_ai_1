export const parseSupplyId = (value: string | null): number | null => {
  if (!value) return null;
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : null;
};

export const isInsufficientStockError = (message: string): boolean =>
  message.toLowerCase().includes("insufficient stock");

export const pluralUnit = (unit: string, count: number): string =>
  count === 1 ? unit : `${unit}s`;

export const FORM_INPUT_CLASS =
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500";

export const FORM_LABEL_CLASS = "text-sm font-medium text-slate-700";
