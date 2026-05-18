"use client";

import { ListActions } from "@/components/candidate-list/list-actions";
import { PageHeader } from "@/components/page-header";
import { CandidateCards } from "@/components/candidate-list/candidate-cards";
import { CandidateFilters } from "@/components/candidate-list/candidate-filters";
import { CandidateTable } from "@/components/candidate-list/candidate-table";
import { PaginationControls } from "@/components/candidate-list/pagination-controls";
import { useCandidateList } from "@/components/candidate-list/use-candidate-list";
import { deleteCandidate } from "@/lib/api";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { LoadingState } from "@/components/states/loading-state";
import { useState } from "react";

export const CandidateListPageClient = () => {
  const { query, result, candidates, loading, error, totalPages, setQueryParam, clearFilters, setPage, retry } = useCandidateList();
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
    <div className="min-h-screen">
      <PageHeader
        title="Talent Pipeline"
        subtitle={`${result?.total ?? 0} total candidates`}
        centeredHeading
        action={<ListActions returnTo={query.returnTo} />}
      />
      <main className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6 sm:px-6 lg:px-8">
        <CandidateFilters
          search={query.search}
          status={query.status}
          stage={query.stage}
          onChange={setQueryParam}
          onClear={clearFilters}
        />

        <section className="flex min-h-[26rem] flex-col overflow-hidden rounded-xl border border-[var(--hc-border)] bg-[var(--hc-surface)]">
          <div className="flex-1">
            <CandidateCards candidates={candidates} returnTo={query.returnTo} deletingId={deletingId} onDelete={handleDelete} />
            <CandidateTable candidates={candidates} returnTo={query.returnTo} deletingId={deletingId} onDelete={handleDelete} />
            {loading ? <LoadingState message="Loading candidates..." /> : null}
            {error ? <ErrorState message={error} onRetry={retry} /> : null}
            {!loading && !error && candidates.length === 0 ? <EmptyState message="No candidates match your filters." /> : null}
          </div>
          <PaginationControls page={result?.page ?? query.page} totalPages={totalPages} onPageChange={setPage} />
        </section>
      </main>
    </div>
  );
};
