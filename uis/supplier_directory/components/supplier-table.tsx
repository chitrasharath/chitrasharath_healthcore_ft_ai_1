import Link from "next/link";

import { formatCategoryLabels } from "@/lib/categories";
import { supplierDetailPath } from "@/lib/supplier-filter-params";
import { formatCompliance, formatRate, formatRateUpdated } from "@/lib/format";
import type { Supplier } from "@/lib/types";

import { SupplierRowActions } from "@/components/supplier-row-actions";
import { SupplierStatusBadge } from "@/components/supplier-status-badge";

type SupplierTableProps = {
  suppliers: Supplier[];
  listQuery: string;
  onUpdateRate: (id: number, rate: number) => Promise<void>;
  onToggleStatus: (supplier: Supplier) => Promise<void>;
};

export const SupplierTable = ({
  suppliers,
  listQuery,
  onUpdateRate,
  onToggleStatus,
}: SupplierTableProps) => (
  <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
    <table className="min-w-full divide-y divide-slate-200 text-sm">
      <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
        <tr>
          <th className="px-4 py-3">Name</th>
          <th className="px-4 py-3">Country</th>
          <th className="px-4 py-3">Categories</th>
          <th className="px-4 py-3">Monthly rate</th>
          <th className="px-4 py-3">Rate updated</th>
          <th className="px-4 py-3">Compliance</th>
          <th className="px-4 py-3">Status</th>
          <th className="px-4 py-3">Actions</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100">
        {suppliers.map((supplier) => (
          <tr
            key={supplier.id}
            className={supplier.status === "suspended" ? "bg-slate-50/80 text-slate-600" : undefined}
          >
            <td className="px-4 py-3 font-medium text-slate-900">
              <Link
                href={supplierDetailPath(supplier.id, listQuery)}
                className="text-sky-800 hover:underline"
              >
                {supplier.name}
              </Link>
            </td>
            <td className="px-4 py-3">{supplier.country}</td>
            <td className="px-4 py-3">{formatCategoryLabels(supplier.categories)}</td>
            <td className="px-4 py-3">{formatRate(supplier)}</td>
            <td className="px-4 py-3">{formatRateUpdated(supplier.rate_updated_at)}</td>
            <td className="px-4 py-3">{formatCompliance(supplier.compliance_agreement)}</td>
            <td className="px-4 py-3">
              <SupplierStatusBadge status={supplier.status} />
            </td>
            <td className="px-4 py-3">
              <SupplierRowActions
                supplier={supplier}
                onUpdateRate={onUpdateRate}
                onToggleStatus={onToggleStatus}
              />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);
