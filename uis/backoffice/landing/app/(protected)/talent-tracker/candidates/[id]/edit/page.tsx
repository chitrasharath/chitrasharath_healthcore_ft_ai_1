"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";

import { EditFormSections } from "@backoffice/talent-tracker/components/candidate-edit/edit-form-sections";
import { ArrowLeftIcon } from "@backoffice/talent-tracker/components/icons";
import { useCandidateEdit } from "@backoffice/talent-tracker/components/candidate-edit/use-candidate-edit";
import { PageHeader } from "@backoffice/talent-tracker/components/page-header";
import { ErrorState } from "@backoffice/talent-tracker/components/states/error-state";
import { LoadingState } from "@backoffice/talent-tracker/components/states/loading-state";
import { TALENT_TRACKER_HOME, talentPath } from "@backoffice/talent-tracker/lib/paths";

const CandidateEditPage = () => {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const notesOpenByDefault = searchParams.get("notes") === "open";
  const returnTo = searchParams.get("returnTo") || TALENT_TRACKER_HOME;
  const edit = useCandidateEdit(params.id, notesOpenByDefault);

  return (
    <>
      <PageHeader title="Edit candidate" subtitle="Update pipeline and profile details" backHref={returnTo} />
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        {edit.loading ? <LoadingState message="Loading candidate..." /> : null}
        {edit.error ? <ErrorState message={edit.error} onRetry={edit.retryLoad} /> : null}

        {!edit.loading && !edit.error ? <EditFormSections edit={edit} /> : null}

        {edit.statusMessage ? <StatusMessage message={edit.statusMessage} statusKind={edit.statusKind} /> : null}

        <Link
          href={`${talentPath(`/candidates/${params.id}`)}?returnTo=${encodeURIComponent(returnTo)}`}
          className="inline-flex w-max items-center gap-2 rounded-md border border-[var(--hc-border)] bg-white px-3 py-2 text-sm"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Back to Candidate Detail
        </Link>
      </main>
    </>
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
