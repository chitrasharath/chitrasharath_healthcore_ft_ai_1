import { EditIcon, EyeIcon, NoteIcon, TrashIcon } from "@backoffice/talent-tracker/components/icons";
import { IconLink } from "@backoffice/talent-tracker/components/icon-link";
import { IconButton } from "@backoffice/talent-tracker/components/icon-button";
import { talentPath } from "@backoffice/talent-tracker/lib/paths";

import type { CandidateRecord } from "@backoffice/talent-tracker/types/candidate";

type CandidateCardsProps = {
  candidates: CandidateRecord[];
  returnTo: string;
  deletingId: string | null;
  onDelete: (candidateId: string) => void;
};

export const CandidateCards = ({
  candidates,
  returnTo,
  deletingId,
  onDelete,
}: CandidateCardsProps) => {
  return (
    <div className="space-y-3 p-3 md:hidden">
      {candidates.map((candidate) => (
        <article key={candidate.id} className="rounded-lg border border-[var(--hc-border)] bg-white p-3">
          <h3 className="text-base font-semibold">{candidate.full_name}</h3>
          <p className="text-sm text-[var(--hc-text-muted)]">{candidate.email}</p>
          <p className="text-sm text-[var(--hc-text-muted)]">{candidate.position}</p>
          <div className="mt-2 flex gap-2 text-xs">
            <span className="rounded-full bg-sky-50 px-2 py-1 text-[var(--hc-brand-strong)]">
              {candidate.status}
            </span>
            <span className="rounded-full bg-slate-100 px-2 py-1 text-[var(--hc-text-muted)]">
              {candidate.stage}
            </span>
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            <IconLink
              href={`${talentPath(`/candidates/${candidate.id}`)}?returnTo=${encodeURIComponent(returnTo)}`}
              label="View candidate"
              icon={<EyeIcon className="h-4 w-4" aria-hidden />}
            />
            <IconLink
              href={`${talentPath(`/candidates/${candidate.id}/edit`)}?returnTo=${encodeURIComponent(returnTo)}`}
              label="Edit candidate"
              icon={<EditIcon className="h-4 w-4" aria-hidden />}
            />
            <IconLink
              href={`${talentPath(`/candidates/${candidate.id}`)}?notes=open&focusNote=1&from=list&returnTo=${encodeURIComponent(returnTo)}`}
              label="Add note"
              icon={<NoteIcon className="h-4 w-4" aria-hidden />}
            />
            <IconButton
              label="Delete candidate"
              icon={<TrashIcon className="h-4 w-4" aria-hidden />}
              onClick={() => onDelete(candidate.id)}
              disabled={deletingId === candidate.id}
            />
          </div>
        </article>
      ))}
    </div>
  );
};

