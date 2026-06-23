"use client";

import { ListActions } from "@backoffice/talent-tracker/components/candidate-list/list-actions";
import { TalentHeader } from "@backoffice/talent-tracker/components/layout/talent-header";
import { CandidateCards } from "@backoffice/talent-tracker/components/candidate-list/candidate-cards";
import { CandidateFilters } from "@backoffice/talent-tracker/components/candidate-list/candidate-filters";
import { CandidateTable } from "@backoffice/talent-tracker/components/candidate-list/candidate-table";
import { PaginationControls } from "@backoffice/talent-tracker/components/candidate-list/pagination-controls";
import { useCandidateList } from "@backoffice/talent-tracker/components/candidate-list/use-candidate-list";
import { deleteCandidate } from "@backoffice/talent-tracker/lib/api";
import { EmptyState } from "@backoffice/talent-tracker/components/states/empty-state";
import { ErrorState } from "@backoffice/talent-tracker/components/states/error-state";
import { LoadingState } from "@backoffice/talent-tracker/components/states/loading-state";
import { useState } from "react";

export const CandidateListPageClient = () => {
  const { query, result, candidates, loading, error, totalPages, setQueryParam, clearFilters, setPage, retry } =
    useCandidateList();
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (candidateId: string) => {
    const allowed = window.confirm("Delete this candidate?");
    if (!allowed) return;

    try {
      setDeletingId(candidateId);
      await deleteCandidate(candidateId);
      retry();
    } catch {
      // keep existing list error behavior from retry path
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <TalentHeader totalCandidates={result?.total ?? 0} />

      <div className="flex justify-end">
        <ListActions returnTo={query.returnTo} />
      </div>

      <CandidateFilters
        search={query.search}
        status={query.status}
        stage={query.stage}
        onChange={setQueryParam}
        onClear={clearFilters}
      />

      {loading ? <LoadingState message="Loading candidates..." /> : null}
      {error ? <ErrorState message={error} onRetry={retry} /> : null}

      {!loading && !error && candidates.length > 0 ? (
        <>
          <CandidateTable
            candidates={candidates}
            returnTo={query.returnTo}
            deletingId={deletingId}
            onDelete={handleDelete}
          />
          <CandidateCards
            candidates={candidates}
            returnTo={query.returnTo}
            deletingId={deletingId}
            onDelete={handleDelete}
          />
          <PaginationControls page={result?.page ?? query.page} totalPages={totalPages} onPageChange={setPage} />
        </>
      ) : null}

      {!loading && !error && candidates.length === 0 ? (
        <EmptyState message="No candidates match your filters." />
      ) : null}
    </main>
  );
};
