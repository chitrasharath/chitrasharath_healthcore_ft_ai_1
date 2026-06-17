"use client";

import { AddSupplierForm } from "@/components/add-supplier-form";
import { SupplierHeader } from "@/components/layout/supplier-header";
import { SupplierFilters } from "@/components/supplier-filters";
import { SupplierTable } from "@/components/supplier-table";
import { useSuppliers } from "@/hooks/use-suppliers";

export const SupplierDirectory = () => {
  const {
    suppliers,
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
  } = useSuppliers();

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <SupplierHeader />
      <AddSupplierForm onSubmit={addSupplier} />
      <SupplierFilters
        countryFilter={countryFilter}
        categoryFilter={categoryFilter}
        apiFiltersEnabled={apiFiltersEnabled}
        onCountryChange={setCountryFilter}
        onCategoryChange={setCategoryFilter}
        onApiFiltersToggle={toggleApiFilters}
      />
      {loading ? <p className="text-sm font-medium text-sky-800">Loading suppliers…</p> : null}
      {error ? (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      ) : null}
      {!loading && !error ? (
        <SupplierTable suppliers={suppliers} onUpdateRate={updateRate} onToggleStatus={toggleStatus} />
      ) : null}
    </main>
  );
};
