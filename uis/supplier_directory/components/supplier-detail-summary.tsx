import { formatCategoryLabels } from "@/lib/categories";
import { formatCompliance, formatRate, formatRateUpdated } from "@/lib/format";
import type { Supplier } from "@/lib/types";

import { SupplierStatusBadge } from "@/components/supplier-status-badge";

type SupplierDetailSummaryProps = {
  supplier: Supplier;
};

export const SupplierDetailSummary = ({ supplier }: SupplierDetailSummaryProps) => (
  <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h2 className="text-xl font-bold text-slate-900">{supplier.name}</h2>
      <SupplierStatusBadge status={supplier.status} />
    </div>
    <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
      <div>
        <dt className="font-medium text-slate-500">Country</dt>
        <dd className="text-slate-900">{supplier.country}</dd>
      </div>
      <div>
        <dt className="font-medium text-slate-500">Categories</dt>
        <dd className="text-slate-900">{formatCategoryLabels(supplier.categories)}</dd>
      </div>
      <div>
        <dt className="font-medium text-slate-500">Monthly rate</dt>
        <dd className="text-slate-900">{formatRate(supplier)}</dd>
      </div>
      <div>
        <dt className="font-medium text-slate-500">Rate updated</dt>
        <dd className="text-slate-900">{formatRateUpdated(supplier.rate_updated_at)}</dd>
      </div>
      <div>
        <dt className="font-medium text-slate-500">Compliance (current)</dt>
        <dd className="text-slate-900">{formatCompliance(supplier.compliance_agreement)}</dd>
      </div>
    </dl>
  </section>
);
