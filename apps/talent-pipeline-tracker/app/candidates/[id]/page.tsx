import { notFound } from "next/navigation";

import { CandidateDetailNotesPanel } from "@/components/candidate-detail-notes-panel";
import { CandidateSummaryCard } from "@/components/candidate-summary-card";
import { PageHeader } from "@/components/page-header";
import { getCandidateById } from "@/lib/api";

type CandidateDetailPageProps = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ returnTo?: string; notes?: string; focusNote?: string }>;
};

const CandidateDetailPage = async ({ params, searchParams }: CandidateDetailPageProps) => {
  const { id } = await params;
  const { returnTo, notes, focusNote } = await searchParams;
  const backHref = returnTo || "/";
  const openNotes = notes === "open";
  const autoFocusInput = focusNote === "1";
  let candidate;

  try {
    candidate = await getCandidateById(id);
  } catch {
    notFound();
  }

  if (!candidate) {
    notFound();
  }

  return (
    <div className="min-h-screen">
      <PageHeader
        title="Talent Pipeline"
        subtitle="Candidate details"
        centeredHeading
        backHref={backHref}
      />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <CandidateSummaryCard
          fullName={candidate.full_name}
          position={candidate.position}
          email={candidate.email}
          phone={candidate.phone}
          linkedinUrl={candidate.linkedin_url}
          cvUrl={candidate.cv_url}
          status={candidate.status}
          stage={candidate.stage}
          experienceYears={candidate.experience_years}
          appliedAt={candidate.applied_at}
        />

        <div className="mt-4">
          <CandidateDetailNotesPanel
            candidateId={candidate.id}
            openByDefault={openNotes}
            autoFocusInput={autoFocusInput}
          />
        </div>
      </main>
    </div>
  );
};

export default CandidateDetailPage;
