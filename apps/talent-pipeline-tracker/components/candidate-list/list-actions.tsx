import Link from "next/link";

import { PlusIcon } from "@/components/icons";

export const ListActions = ({ returnTo }: { returnTo: string }) => {
  return (
    <div className="flex items-center gap-2">
      <Link
        href={`/candidates/new?returnTo=${encodeURIComponent(returnTo)}`}
        className="inline-flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold text-[var(--hc-brand)] hover:bg-[var(--hc-surface-muted)] hover:text-[var(--hc-brand-strong)] sm:w-auto sm:bg-[var(--hc-brand)] sm:px-3 sm:py-2 sm:text-sm sm:text-white sm:hover:bg-[var(--hc-brand-strong)] sm:hover:text-white"
      >
        <PlusIcon className="h-4 w-4" />
        <span>New Candidate</span>
      </Link>
    </div>
  );
};