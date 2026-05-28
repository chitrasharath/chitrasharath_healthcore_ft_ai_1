import Link from "next/link";
import type { ReactNode } from "react";

import { HealthCoreLogo } from "@/components/healthcore-logo";
import { ArrowLeftIcon, MenuIcon } from "@/components/icons";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  backHref?: string;
  centeredHeading?: boolean;
};

export const PageHeader = ({
  title,
  subtitle,
  action,
  backHref,
  centeredHeading,
}: PageHeaderProps) => {
  return (
    <header className="sticky top-0 z-10 border-b border-[var(--hc-border)] bg-white/95 backdrop-blur">
      <div className="relative mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-2.5 sm:gap-4 sm:px-6 sm:py-3 lg:px-8">
        <div className="flex min-w-0 items-start gap-3 sm:gap-4">
          <div className="flex min-w-0 flex-col items-start gap-1">
            <HealthCoreLogo />
          {backHref ? (
            <Link
              href={backHref}
              className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--hc-brand)] hover:text-[var(--hc-brand-strong)] sm:text-sm"
            >
              <ArrowLeftIcon className="h-4 w-4" />
              Back to list
            </Link>
          ) : null}
          </div>
          <div className="min-w-0 text-right sm:text-left">
            {!centeredHeading ? <h1 className="truncate text-base font-bold text-[var(--hc-text)] sm:text-xl">{title}</h1> : null}
            {!centeredHeading && subtitle ? <p className="truncate text-[11px] text-[var(--hc-text-muted)] sm:text-sm">{subtitle}</p> : null}
          </div>
        </div>

        {centeredHeading ? (
          <div className="pointer-events-none absolute inset-y-0 left-28 right-14 flex flex-col items-end justify-center text-right sm:left-44 sm:right-20 sm:items-center sm:text-center">
            <h1 className="w-full truncate text-base font-bold text-[var(--hc-text)] sm:text-xl">{title}</h1>
            {subtitle ? <p className="w-full truncate text-[11px] text-[var(--hc-text-muted)] sm:text-sm">{subtitle}</p> : null}
          </div>
        ) : null}

        {action ? (
          <>
            <div className="ml-auto hidden sm:block">{action}</div>
            <details className="relative ml-auto sm:hidden">
              <summary className="inline-flex h-9 w-9 list-none items-center justify-center rounded-md border border-[var(--hc-border)] text-[var(--hc-text)] hover:bg-[var(--hc-surface-muted)] [&::-webkit-details-marker]:hidden">
                <MenuIcon className="h-5 w-5" />
                <span className="sr-only">Open header menu</span>
              </summary>
              <div className="absolute right-0 mt-2 w-max min-w-[11rem] rounded-md border border-[var(--hc-border)] bg-white p-2 shadow-lg">
                {action}
              </div>
            </details>
          </>
        ) : null}
      </div>
    </header>
  );
};
