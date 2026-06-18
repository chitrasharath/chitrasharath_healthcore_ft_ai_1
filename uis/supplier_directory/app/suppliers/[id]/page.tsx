import { Suspense } from "react";

import { SupplierDetail } from "@/components/supplier-detail";

type SupplierDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function SupplierDetailPage({ params }: SupplierDetailPageProps) {
  const { id } = await params;
  const supplierId = Number(id);
  if (!Number.isInteger(supplierId) || supplierId <= 0) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8">
        <p className="text-sm text-red-600">Invalid supplier ID.</p>
      </main>
    );
  }
  return (
    <Suspense fallback={<p className="px-4 py-8 text-sm font-medium text-sky-800">Loading supplier…</p>}>
      <SupplierDetail supplierId={supplierId} />
    </Suspense>
  );
}
