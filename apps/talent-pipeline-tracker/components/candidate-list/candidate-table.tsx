import { EditIcon, EyeIcon, NoteIcon, TrashIcon } from "@/components/icons";
import { IconLink } from "@/components/icon-link";
import { IconButton } from "@/components/icon-button";

import type { CandidateRecord } from "@/types/candidate";

type CandidateTableProps = {
  candidates: CandidateRecord[];
  returnTo: string;
  deletingId: string | null;
  onDelete: (candidateId: string) => void;
};

export const CandidateTable = ({
  candidates,
  returnTo,
  deletingId,
  onDelete,
}: CandidateTableProps) => {
  return (
    <div className="hidden md:block">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-[var(--hc-surface-muted)] text-[var(--hc-text-muted)]">
          <tr>
            <th className="px-4 py-3">Full Name</th>
            <th className="px-4 py-3">Email</th>
            <th className="px-4 py-3">Position</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Stage</th>
            <th className="px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((candidate) => (
            <tr key={candidate.id} className="border-t border-[var(--hc-border)]">
              <td className="px-4 py-3 font-medium">{candidate.full_name}</td>
              <td className="px-4 py-3">{candidate.email}</td>
              <td className="px-4 py-3">{candidate.position}</td>
              <td className="px-4 py-3">{candidate.status}</td>
              <td className="px-4 py-3">{candidate.stage}</td>
              <td className="px-4 py-3">
                <CandidateActions
                  candidateId={candidate.id}
                  returnTo={returnTo}
                  deleting={deletingId === candidate.id}
                  onDelete={onDelete}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const CandidateActions = ({
  candidateId,
  returnTo,
  deleting,
  onDelete,
}: {
  candidateId: string;
  returnTo: string;
  deleting: boolean;
  onDelete: (candidateId: string) => void;
}) => {
  return (
    <div className="flex gap-2">
      <IconLink
        href={`/candidates/${candidateId}?returnTo=${encodeURIComponent(returnTo)}`}
        label="View candidate"
        icon={<EyeIcon className="h-4 w-4" />}
      />
      <IconLink
        href={`/candidates/${candidateId}/edit?returnTo=${encodeURIComponent(returnTo)}`}
        label="Edit candidate"
        icon={<EditIcon className="h-4 w-4" />}
      />
      <IconLink
        href={`/candidates/${candidateId}?notes=open&focusNote=1&from=list&returnTo=${encodeURIComponent(returnTo)}`}
        label="Add note"
        icon={<NoteIcon className="h-4 w-4" />}
      />
      <IconButton
        type="button"
        label="Delete candidate"
        icon={<TrashIcon className="h-4 w-4" />}
        onClick={() => onDelete(candidateId)}
        disabled={deleting}
      />
    </div>
  );
};

