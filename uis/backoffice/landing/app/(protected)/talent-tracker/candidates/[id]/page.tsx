import { notFound } from "next/navigation";

import { CandidateDetailNotesPanel } from "@backoffice/talent-tracker/components/candidate-detail-notes-panel";
import { CandidateSummaryCard } from "@backoffice/talent-tracker/components/candidate-summary-card";
import { PageHeader } from "@backoffice/talent-tracker/components/page-header";
import { getCandidateById } from "@backoffice/talent-tracker/lib/api";
import { TALENT_TRACKER_HOME } from "@backoffice/talent-tracker/lib/paths";

type CandidateDetailPageProps = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ returnTo?: string; notes?: string; focusNote?: string }>;
};

export default async function CandidateDetailPage({ params, searchParams }: CandidateDetailPageProps) {
  const { id } = await params;
  const { returnTo, notes, focusNote } = await searchParams;
  const backHref = returnTo || TALENT_TRACKER_HOME;
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
    <>
      <PageHeader title={candidate.full_name} subtitle={candidate.position} backHref={backHref} />
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
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
    </>
  );
}
