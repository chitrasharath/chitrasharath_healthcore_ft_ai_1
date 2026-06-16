"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createSupplier,
  listSuppliers,
  updateSupplierRate,
  updateSupplierStatus,
} from "@/lib/api";
import type { Supplier, SupplierCreateInput } from "@/lib/types";

export const useSuppliers = () => {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [countryFilter, setCountryFilter] = useState<"all" | "USA" | "UK">("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");

  const load = useCallback(async () => {
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

  useEffect(() => {
    // Initial fetch on mount — standard data-loading pattern for client dashboards.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    return suppliers.filter((supplier) => {
      if (countryFilter !== "all" && supplier.country !== countryFilter) return false;
      if (categoryFilter !== "all" && !supplier.categories.includes(categoryFilter)) return false;
      return true;
    });
  }, [suppliers, countryFilter, categoryFilter]);

  const replaceSupplier = (updated: Supplier) => {
    setSuppliers((current) => current.map((s) => (s.id === updated.id ? updated : s)));
  };

  const addSupplier = async (input: SupplierCreateInput): Promise<void> => {
    const created = await createSupplier(input);
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

  return {
    suppliers: filtered,
    loading,
    error,
    countryFilter,
    categoryFilter,
    setCountryFilter,
    setCategoryFilter,
    addSupplier,
    updateRate,
    toggleStatus,
    reload: load,
  };
};
