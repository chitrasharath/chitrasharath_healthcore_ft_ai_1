import { Suspense } from "react";

import { NewCandidatePageClient } from "@backoffice/talent-tracker/components/new-candidate-page";

export default function NewCandidatePage() {
  return (
    <Suspense fallback={<div className="p-4 text-sm">Loading page...</div>}>
      <NewCandidatePageClient />
    </Suspense>
  );
}
