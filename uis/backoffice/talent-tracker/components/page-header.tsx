import Link from "next/link";
import type { ReactNode } from "react";

import { ArrowLeftIcon } from "@backoffice/talent-tracker/components/icons";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  backHref?: string;
  backLabel?: string;
};

export const PageHeader = ({ title, subtitle, action, backHref, backLabel = "Back to list" }: PageHeaderProps) => {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <div className="min-w-0 flex-1 space-y-1">
          {backHref ? (
            <Link
              href={backHref}
              className="inline-flex items-center gap-1 text-sm font-semibold text-sky-800 hover:underline"
            >
              <ArrowLeftIcon className="h-4 w-4" />
              {backLabel}
            </Link>
          ) : null}
          <h1 className="text-lg font-bold text-slate-900 sm:text-xl">{title}</h1>
          {subtitle ? <p className="text-sm text-slate-600">{subtitle}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
    </header>
  );
};
