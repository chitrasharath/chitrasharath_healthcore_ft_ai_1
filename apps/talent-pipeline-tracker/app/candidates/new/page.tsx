import { Suspense } from "react";

import { NewCandidatePageClient } from "@/components/new-candidate-page";

const NewCandidatePage = () => {
  return (
    <Suspense fallback={<div className="p-4 text-sm">Loading page...</div>}>
      <NewCandidatePageClient />
    </Suspense>
  );
};

export default NewCandidatePage;
