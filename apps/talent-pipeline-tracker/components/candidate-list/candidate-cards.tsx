import { EditIcon, EyeIcon, NoteIcon, TrashIcon } from "@/components/icons";
import { IconLink } from "@/components/icon-link";
import { IconButton } from "@/components/icon-button";

import type { CandidateRecord } from "@/types/candidate";

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
          <div className="mt-3 flex flex-wrap gap-2 text-sm">
            <IconLink
              href={`/candidates/${candidate.id}?returnTo=${encodeURIComponent(returnTo)}`}
              label="View"
              compact={false}
              icon={<EyeIcon className="h-4 w-4" />}
            />
            <IconLink
              href={`/candidates/${candidate.id}/edit?returnTo=${encodeURIComponent(returnTo)}`}
              label="Edit"
              compact={false}
              icon={<EditIcon className="h-4 w-4" />}
            />
            <IconLink
              href={`/candidates/${candidate.id}?notes=open&focusNote=1&from=list&returnTo=${encodeURIComponent(returnTo)}`}
              label="Add Note"
              compact={false}
              icon={<NoteIcon className="h-4 w-4" />}
            />
            <IconButton
              type="button"
              compact={false}
              label="Delete"
              icon={<TrashIcon className="h-4 w-4" />}
              onClick={() => onDelete(candidate.id)}
              disabled={deletingId === candidate.id}
            />
          </div>
        </article>
      ))}
    </div>
  );
};

