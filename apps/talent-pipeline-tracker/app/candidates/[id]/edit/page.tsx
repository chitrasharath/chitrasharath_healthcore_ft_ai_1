"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";

import { EditFormSections } from "@/components/candidate-edit/edit-form-sections";
import { ArrowLeftIcon } from "@/components/icons";
import { useCandidateEdit } from "@/components/candidate-edit/use-candidate-edit";
import { PageHeader } from "@/components/page-header";
import { ErrorState } from "@/components/states/error-state";
import { LoadingState } from "@/components/states/loading-state";

const CandidateEditPage = () => {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const notesOpenByDefault = searchParams.get("notes") === "open";
  const returnTo = searchParams.get("returnTo") || "/";
  const edit = useCandidateEdit(params.id, notesOpenByDefault);

  return (
    <div className="min-h-screen">
      <PageHeader
          title="Talent Pipeline"
        subtitle="Candidate details"
        centeredHeading
        backHref={returnTo}
      />
      <main className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6 sm:px-6 lg:px-8">
        {edit.loading ? <LoadingState message="Loading candidate..." /> : null}
        {edit.error ? <ErrorState message={edit.error} onRetry={edit.retryLoad} /> : null}

        {!edit.loading && !edit.error ? <EditFormSections edit={edit} /> : null}

        {edit.statusMessage ? <StatusMessage message={edit.statusMessage} statusKind={edit.statusKind} /> : null}

        <Link
          href={`/candidates/${params.id}?returnTo=${encodeURIComponent(returnTo)}`}
          className="inline-flex w-max items-center gap-2 rounded-md border border-[var(--hc-border)] bg-white px-3 py-2 text-sm"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Back to Candidate Detail
        </Link>
      </main>
    </div>
  );
};

export default CandidateEditPage;

const StatusMessage = ({
  message,
  statusKind,
}: {
  message: string;
  statusKind: "success" | "error";
}) => {
  return (
    <p
      aria-live={statusKind === "error" ? "assertive" : "polite"}
      className={`text-sm ${statusKind === "error" ? "text-[var(--hc-danger)]" : "text-[var(--hc-success)]"}`}
    >
      {message}
    </p>
  );
};
