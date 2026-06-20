import Link from "next/link";

import { EditIcon, EyeIcon, NoteIcon, TrashIcon } from "@backoffice/talent-tracker/components/icons";
import { IconLink } from "@backoffice/talent-tracker/components/icon-link";
import { IconButton } from "@backoffice/talent-tracker/components/icon-button";
import { talentPath } from "@backoffice/talent-tracker/lib/paths";

import type { CandidateRecord } from "@backoffice/talent-tracker/types/candidate";

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
    <div className="hidden overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm md:block">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
          <tr>
            <th className="px-4 py-3">Full name</th>
            <th className="px-4 py-3">Email</th>
            <th className="px-4 py-3">Position</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Stage</th>
            <th className="px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {candidates.map((candidate) => (
            <tr key={candidate.id}>
              <td className="px-4 py-3 font-medium text-slate-900">
                <Link
                  href={`${talentPath(`/candidates/${candidate.id}`)}?returnTo=${encodeURIComponent(returnTo)}`}
                  className="text-sky-800 hover:underline"
                >
                  {candidate.full_name}
                </Link>
              </td>
              <td className="px-4 py-3 text-slate-700">{candidate.email}</td>
              <td className="px-4 py-3 text-slate-700">{candidate.position}</td>
              <td className="px-4 py-3 capitalize text-slate-700">{candidate.status.replace(/_/g, " ")}</td>
              <td className="px-4 py-3 capitalize text-slate-700">{candidate.stage.replace(/_/g, " ")}</td>
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
    <div className="flex flex-nowrap items-center gap-1.5">
      <IconLink
        href={`${talentPath(`/candidates/${candidateId}`)}?returnTo=${encodeURIComponent(returnTo)}`}
        label="View candidate"
        icon={<EyeIcon className="h-4 w-4" aria-hidden />}
      />
      <IconLink
        href={`${talentPath(`/candidates/${candidateId}/edit`)}?returnTo=${encodeURIComponent(returnTo)}`}
        label="Edit candidate"
        icon={<EditIcon className="h-4 w-4" aria-hidden />}
      />
      <IconLink
        href={`${talentPath(`/candidates/${candidateId}`)}?notes=open&focusNote=1&from=list&returnTo=${encodeURIComponent(returnTo)}`}
        label="Add note"
        icon={<NoteIcon className="h-4 w-4" aria-hidden />}
      />
      <IconButton
        label="Delete candidate"
        icon={<TrashIcon className="h-4 w-4" aria-hidden />}
        onClick={() => onDelete(candidateId)}
        disabled={deleting}
      />
    </div>
  );
};
