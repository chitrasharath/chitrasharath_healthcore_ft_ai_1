import type { Supplier } from "@/lib/types";

export const formatRate = (supplier: Supplier): string => {
  const value = supplier.monthly_rate.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return supplier.currency === "USD" ? `$${value}` : `£${value}`;
};

export const formatRateUpdated = (value: string): string =>
  new Date(value).toLocaleString();

export const formatCompliance = (value: string | null): string => value ?? "—";
