"use client";

import { EmptyState } from "@backoffice/inventory/components/empty-state";
import { useInventoryTimezone } from "@backoffice/inventory/components/inventory-timezone-context";
import { InventoryPageHeader } from "@backoffice/inventory/components/inventory-page-header";
import { OrdersTableBody } from "@backoffice/inventory/components/orders-table-body";
import { StatusBanner } from "@backoffice/inventory/components/status-banner";
import { useOrders } from "@backoffice/inventory/hooks/use-orders";

export const OrdersTable = () => {
  const { orders, loading, error } = useOrders();
  const { timezone } = useInventoryTimezone();

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
      <InventoryPageHeader
        title="Order History"
        subtitle="View all supply deliveries and consumptions."
      />
      {error ? <StatusBanner variant="error" message={error} /> : null}
      {loading ? <p className="text-sm text-slate-500">Loading orders…</p> : null}
      {!loading && !error && orders.length === 0 ? (
        <EmptyState message="No orders yet." />
      ) : null}
      {!loading && orders.length > 0 ? (
        <div className="mt-4 overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Supply Name</th>
                <th className="px-4 py-3">Quantity</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Clinic</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">User UUID</th>
              </tr>
            </thead>
            <OrdersTableBody orders={orders} timeZone={timezone} />
          </table>
        </div>
      ) : null}
    </main>
  );
};
