import { Suspense } from "react";

import { ManualTestPage } from "@backoffice/backoffice-functions/components/manual-test-page";

export default function Page() {
  return (
    <Suspense fallback={<p className="p-6 text-sm text-slate-700">Loading manual test dashboard…</p>}>
      <ManualTestPage />
    </Suspense>
  );
}
