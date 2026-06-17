"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createSupplier,
  listSuppliers,
  updateSupplierRate,
  updateSupplierStatus,
} from "@/lib/api";
import type { Supplier, SupplierCreateInput } from "@/lib/types";

const matchesFilters = (
  supplier: Supplier,
  countryFilter: "all" | "USA" | "UK",
  categoryFilter: string,
) => {
  if (countryFilter !== "all" && supplier.country !== countryFilter) return false;
  if (categoryFilter !== "all" && !supplier.categories.includes(categoryFilter)) return false;
  return true;
};

export const useSuppliers = () => {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [countryFilter, setCountryFilter] = useState<"all" | "USA" | "UK">("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [apiFiltersEnabled, setApiFiltersEnabled] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSuppliers(await listSuppliers());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load suppliers");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchFiltered = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSuppliers(
        await listSuppliers({
          country: countryFilter === "all" ? undefined : countryFilter,
          category: categoryFilter === "all" ? undefined : categoryFilter,
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load suppliers");
    } finally {
      setLoading(false);
    }
  }, [countryFilter, categoryFilter]);

  useEffect(() => {
    if (apiFiltersEnabled) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchAll();
  }, [apiFiltersEnabled, fetchAll]);

  useEffect(() => {
    if (!apiFiltersEnabled) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchFiltered();
  }, [apiFiltersEnabled, fetchFiltered]);

  const displayed = useMemo(() => {
    if (apiFiltersEnabled) return suppliers;
    return suppliers.filter((supplier) => matchesFilters(supplier, countryFilter, categoryFilter));
  }, [suppliers, apiFiltersEnabled, countryFilter, categoryFilter]);

  const replaceSupplier = (updated: Supplier) => {
    setSuppliers((current) => current.map((s) => (s.id === updated.id ? updated : s)));
  };

  const addSupplier = async (input: SupplierCreateInput): Promise<void> => {
    const created = await createSupplier(input);
    if (apiFiltersEnabled) {
      await fetchFiltered();
      return;
    }
    setSuppliers((current) => [...current, created]);
  };

  const updateRate = async (id: number, monthlyRate: number) => {
    const updated = await updateSupplierRate(id, monthlyRate);
    replaceSupplier(updated);
  };

  const toggleStatus = async (supplier: Supplier) => {
    const next = supplier.status === "active" ? "suspended" : "active";
    const updated = await updateSupplierStatus(supplier.id, next);
    replaceSupplier(updated);
  };

  const toggleApiFilters = () => {
    setApiFiltersEnabled((current) => !current);
  };

  return {
    suppliers: displayed,
    loading,
    error,
    countryFilter,
    categoryFilter,
    apiFiltersEnabled,
    setCountryFilter,
    setCategoryFilter,
    toggleApiFilters,
    addSupplier,
    updateRate,
    toggleStatus,
    reload: () => (apiFiltersEnabled ? fetchFiltered() : fetchAll()),
  };
};
