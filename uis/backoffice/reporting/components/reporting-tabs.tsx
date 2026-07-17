"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { TAB_LABELS } from "@backoffice/reporting/lib/kpi-definitions";
import type { ReportingTab } from "@backoffice/reporting/types/reporting";

const TABS = Object.keys(TAB_LABELS) as ReportingTab[];

type Props = { active: ReportingTab };

export const ReportingTabs = ({ active }: Props) => {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const select = (tab: ReportingTab) => {
    const next = new URLSearchParams(searchParams.toString());
    next.set("tab", tab);
    if (tab === "health") next.delete("month");
    router.replace(`${pathname}?${next.toString()}`);
  };

  return (
    <nav aria-label="Reporting tabs" className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
      {TABS.map((tab) => {
        const isActive = tab === active;
        return (
          <button
            key={tab}
            type="button"
            onClick={() => select(tab)}
            className={
              isActive
                ? "rounded-md bg-sky-700 px-3 py-1.5 text-sm font-semibold text-white"
                : "rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-200"
            }
            aria-current={isActive ? "page" : undefined}
          >
            {TAB_LABELS[tab]}
          </button>
        );
      })}
    </nav>
  );
};
