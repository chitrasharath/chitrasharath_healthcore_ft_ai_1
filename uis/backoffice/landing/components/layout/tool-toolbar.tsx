"use client";

import Link from "next/link";

import { ThemeToggle } from "@backoffice/shared/components/theme-toggle";

export const ToolToolbar = () => {
  const logout = () => {
    localStorage.removeItem("token");
    window.location.href = "/";
  };

  return (
    <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-900 sm:px-6 lg:px-8">
      <Link
        href="/"
        className="text-sm font-semibold text-sky-800 hover:text-sky-950 dark:text-sky-300 dark:hover:text-sky-100"
      >
        ← Back to hub
      </Link>
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <button
          type="button"
          onClick={logout}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          Log Out
        </button>
      </div>
    </div>
  );
};
