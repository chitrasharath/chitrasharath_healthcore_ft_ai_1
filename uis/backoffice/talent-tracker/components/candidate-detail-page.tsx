"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { CandidateDetailNotesPanel } from "@backoffice/talent-tracker/components/candidate-detail-notes-panel";
import { CandidateSummaryCard } from "@backoffice/talent-tracker/components/candidate-summary-card";
import { PageHeader } from "@backoffice/talent-tracker/components/page-header";
import { ErrorState } from "@backoffice/talent-tracker/components/states/error-state";
import { LoadingState } from "@backoffice/talent-tracker/components/states/loading-state";
import { getCandidateById } from "@backoffice/talent-tracker/lib/api";
import { TALENT_TRACKER_HOME } from "@backoffice/talent-tracker/lib/paths";
import type { CandidateRecord } from "@backoffice/talent-tracker/types/candidate";

export const CandidateDetailPageClient = () => {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const returnTo = searchParams.get("returnTo") || TALENT_TRACKER_HOME;
  const openNotes = searchParams.get("notes") === "open";
  const autoFocusInput = searchParams.get("focusNote") === "1";
  const [candidate, setCandidate] = useState<CandidateRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;

    const loadCandidate = async () => {
      setLoading(true);
      setError("");
      try {
        const data = await getCandidateById(params.id);
        if (active) setCandidate(data);
      } catch (loadError) {
        if (active) {
          setCandidate(null);
          setError(loadError instanceof Error ? loadError.message : "Could not load candidate.");
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    void loadCandidate();
    return () => {
      active = false;
    };
  }, [params.id, reloadKey]);

  return (
    <>
      <PageHeader
        title={candidate?.full_name ?? "Candidate"}
        subtitle={candidate?.position ?? ""}
        backHref={returnTo}
      />
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        {loading ? <LoadingState message="Loading candidate..." /> : null}
        {error ? <ErrorState message={error} onRetry={() => setReloadKey((key) => key + 1)} /> : null}
        {!loading && !error && candidate ? (
          <>
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
          </>
        ) : null}
      </main>
    </>
  );
};
