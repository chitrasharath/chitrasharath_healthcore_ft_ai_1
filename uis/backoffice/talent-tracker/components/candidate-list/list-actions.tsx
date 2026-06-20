"use client";

import Link from "next/link";

import { PlusIcon } from "@backoffice/talent-tracker/components/icons";
import { talentPath } from "@backoffice/talent-tracker/lib/paths";

export const ListActions = ({ returnTo }: { returnTo: string }) => {
  return (
    <Link
      href={`${talentPath("/candidates/new")}?returnTo=${encodeURIComponent(returnTo)}`}
      className="inline-flex items-center gap-2 rounded-lg bg-sky-800 px-4 py-2 text-sm font-semibold text-white transition hover:bg-sky-900"
    >
      <PlusIcon className="h-4 w-4" />
      <span>New Candidate</span>
    </Link>
  );
};
