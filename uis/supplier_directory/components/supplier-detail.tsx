"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { SupplierDetailSummary } from "@/components/supplier-detail-summary";
import { SupplierOptionalForm } from "@/components/supplier-optional-form";
import { useSupplierDetail } from "@/hooks/use-supplier-detail";
import { supplierListPathFromReturn } from "@/lib/supplier-filter-params";

type SupplierDetailProps = {
  supplierId: number;
};

export const SupplierDetail = ({ supplierId }: SupplierDetailProps) => {
  const searchParams = useSearchParams();
  const backHref = supplierListPathFromReturn(searchParams.get("return"));
  const { supplier, loading, error, saveDetails } = useSupplierDetail(supplierId);

  return (
    <main className="mx-auto max-w-3xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <Link href={backHref} className="text-sm font-semibold text-sky-800 hover:underline">
        ← Back to directory
      </Link>
      {loading ? <p className="text-sm font-medium text-sky-800">Loading supplier…</p> : null}
      {error ? (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      ) : null}
      {supplier ? (
        <>
          <SupplierDetailSummary supplier={supplier} />
          <SupplierOptionalForm
            supplier={supplier}
            onSave={async (details) => {
              await saveDetails(details);
            }}
          />
        </>
      ) : null}
    </main>
  );
};
