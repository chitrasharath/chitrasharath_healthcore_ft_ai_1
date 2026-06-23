import type { Supplier } from "@backoffice/supplier-directory/lib/types";

const numberFormat = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const dateTimeFormat = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
});

export const formatRate = (supplier: Supplier): string => {
  const value = numberFormat.format(supplier.monthly_rate);
  return supplier.currency === "USD" ? `$${value}` : `£${value}`;
};

export const formatRateUpdated = (value: string): string =>
  dateTimeFormat.format(new Date(value));

export const formatCompliance = (value: string | null): string => value ?? "—";
