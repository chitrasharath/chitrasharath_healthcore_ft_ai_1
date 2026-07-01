"use client";

import Link from "next/link";

type IncidentRowActionsProps = {
  id: number;
};

const linkClass = "text-sm font-semibold text-sky-700 hover:text-sky-900";

export const IncidentRowActions = ({ id }: IncidentRowActionsProps) => (
  <div className="flex items-center justify-center gap-3">
    <Link href={`/incident-manager/${id}`} className={linkClass}>
      View
    </Link>
    <Link href={`/incident-manager/${id}/edit`} className={linkClass}>
      Edit
    </Link>
  </div>
);
