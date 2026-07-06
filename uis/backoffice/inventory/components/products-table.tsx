"use client";

import { EmptyState } from "@backoffice/inventory/components/empty-state";
import { InventoryPageHeader } from "@backoffice/inventory/components/inventory-page-header";
import { ProductsTableBody } from "@backoffice/inventory/components/products-table-body";
import { StatusBanner } from "@backoffice/inventory/components/status-banner";
import { useProducts } from "@backoffice/inventory/hooks/use-products";

export const ProductsTable = () => {
  const { products, loading, error } = useProducts();

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
      <InventoryPageHeader
        title="Supply Stock"
        subtitle="View all medical supplies and current stock levels."
      />
      {error ? <StatusBanner variant="error" message={error} /> : null}
      {loading ? <p className="text-sm text-slate-500">Loading supplies…</p> : null}
      {!loading && !error && products.length === 0 ? (
        <EmptyState message="No supplies found." />
      ) : null}
      {!loading && products.length > 0 ? (
        <div className="mt-4 overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">SKU</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Unit</th>
                <th className="px-4 py-3">Country</th>
                <th className="px-4 py-3">Current Stock</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <ProductsTableBody products={products} />
          </table>
        </div>
      ) : null}
    </main>
  );
};
