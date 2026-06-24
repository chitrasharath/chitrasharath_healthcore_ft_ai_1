import {
  applySupplierFilters,
  filterListQuery,
  parseSupplierFilters,
  supplierDetailPath,
  supplierListPath,
  supplierListPathFromReturn,
} from "@backoffice/supplier-directory/lib/supplier-filter-params";

describe("supplier-filter-params", () => {
  test("parseSupplierFilters — no params returns all defaults", () => {
    expect(parseSupplierFilters(new URLSearchParams())).toEqual({
      countryFilter: "all",
      categoryFilter: "all",
    });
  });

  test("parseSupplierFilters — valid country and category", () => {
    const params = new URLSearchParams("country=USA&category=pharmaceutical");
    expect(parseSupplierFilters(params)).toEqual({
      countryFilter: "USA",
      categoryFilter: "pharmaceutical",
    });
  });

  test("parseSupplierFilters — invalid country falls back to all", () => {
    const params = new URLSearchParams("country=INVALID");
    expect(parseSupplierFilters(params).countryFilter).toBe("all");
  });

  test("parseSupplierFilters — invalid category falls back to all", () => {
    const params = new URLSearchParams("category=nonexistent");
    expect(parseSupplierFilters(params).categoryFilter).toBe("all");
  });

  test("applySupplierFilters — sets country param", () => {
    const next = applySupplierFilters(new URLSearchParams(), { countryFilter: "UK" });
    expect(next.get("country")).toBe("UK");
  });

  test("applySupplierFilters — removes country when all", () => {
    const start = new URLSearchParams("country=USA");
    const next = applySupplierFilters(start, { countryFilter: "all" });
    expect(next.has("country")).toBe(false);
  });

  test("applySupplierFilters — strips api param", () => {
    const start = new URLSearchParams("api=true&country=USA");
    const next = applySupplierFilters(start, {});
    expect(next.has("api")).toBe(false);
  });

  test("filterListQuery — builds query string from filters", () => {
    const params = new URLSearchParams("country=UK&category=pharmaceutical");
    expect(filterListQuery(params)).toBe("country=UK&category=pharmaceutical");
  });

  test("supplierListPath — no filters returns base path", () => {
    expect(supplierListPath(new URLSearchParams())).toBe("/supplier-directory");
  });

  test("supplierDetailPath — with return query", () => {
    expect(supplierDetailPath(42, "country=USA")).toContain("/suppliers/42?return=");
  });

  test("supplierDetailPath — without return query", () => {
    expect(supplierDetailPath(42, "")).toBe("/supplier-directory/suppliers/42");
  });

  test("supplierListPathFromReturn — null return query", () => {
    expect(supplierListPathFromReturn(null)).toBe("/supplier-directory");
  });
});
