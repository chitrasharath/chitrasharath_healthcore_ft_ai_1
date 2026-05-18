import { Suspense } from "react";

import { CandidateListPageClient } from "@/components/candidate-list-page";

const CandidateListPage = () => {
  return (
    <Suspense fallback={<div className="p-4 text-sm">Loading page...</div>}>
      <CandidateListPageClient />
    </Suspense>
  );
};

export default CandidateListPage;
