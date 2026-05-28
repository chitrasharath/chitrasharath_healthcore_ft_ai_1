"use client";

import { usePathname, useSearchParams } from "next/navigation";

export const StickyFooter = () => {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const page = searchParams.get("page") || "1";

  return (
    <footer className="fixed inset-x-0 bottom-0 border-t border-[var(--hc-border)] bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 text-xs text-[var(--hc-text-muted)] sm:text-sm">
        <span>HealthCore Talent Pipeline Tracker</span>
        <span>{footerLabel(pathname, page)}</span>
      </div>
    </footer>
  );
};

const footerLabel = (pathname: string, page: string) => {
  if (pathname === "/") return `Candidate List • Page ${page}`;
  if (pathname === "/candidates/new") return "New Candidate";
  if (pathname.endsWith("/edit")) return "Edit Candidate";
  return "Candidate Detail";
};