import { Suspense } from "react";

import { CandidateListPageClient } from "@backoffice/talent-tracker/components/candidate-list-page";

export default function TalentTrackerPage() {
  return (
    <Suspense fallback={<div className="p-4 text-sm">Loading page...</div>}>
      <CandidateListPageClient />
    </Suspense>
  );
}
