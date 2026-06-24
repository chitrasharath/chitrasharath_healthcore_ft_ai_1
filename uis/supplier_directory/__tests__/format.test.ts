import { formatCompliance, formatRate, formatRateUpdated } from "@backoffice/supplier-directory/lib/format";
import type { Supplier } from "@backoffice/supplier-directory/lib/types";

const usdSupplier = {
  currency: "USD",
  monthly_rate: 1234.5,
} as Supplier;

const gbpSupplier = {
  currency: "GBP",
  monthly_rate: 999,
} as Supplier;

describe("format", () => {
  test("formatRate — USD supplier formats with $", () => {
    expect(formatRate(usdSupplier)).toBe("$1,234.50");
  });

  test("formatRate — GBP supplier formats with £", () => {
    expect(formatRate(gbpSupplier)).toBe("£999.00");
  });

  test("formatRateUpdated — formats ISO date string", () => {
    expect(formatRateUpdated("2025-06-15T10:30:00Z")).toContain("Jun 15, 2025");
  });

  test("formatCompliance — null returns em dash", () => {
    expect(formatCompliance(null)).toBe("—");
  });

  test("formatCompliance — non-null returns value", () => {
    expect(formatCompliance("HIPAA")).toBe("HIPAA");
  });
});
