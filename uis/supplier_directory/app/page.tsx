import { Suspense } from "react";

import { SupplierDirectory } from "@/components/supplier-directory";

export default function Page() {
  return (
    <Suspense fallback={<p className="px-4 py-8 text-sm font-medium text-sky-800">Loading directory…</p>}>
      <SupplierDirectory />
    </Suspense>
  );
}
