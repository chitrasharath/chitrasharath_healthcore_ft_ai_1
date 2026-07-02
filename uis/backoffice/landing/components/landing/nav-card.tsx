import Link from "next/link";

import type { NavApp } from "@/lib/nav-apps";

type NavCardProps = {
  app: NavApp;
};

const cardClassName =
  "group flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-sky-300 hover:shadow-md";

const LockIcon = () => (
  <svg aria-hidden="true" className="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
    />
  </svg>
);

const tagClassName: Record<NonNullable<NavApp["tagVariant"]>, string> = {
  new: "rounded-full bg-teal-100 px-2 py-0.5 text-xs font-semibold text-teal-800",
  deprecated: "rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800",
};

const NavCardContent = ({ app }: NavCardProps) => (
  <>
    <div className="flex items-start justify-between gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold text-slate-900 group-hover:text-sky-800">{app.title}</h3>
        {app.tag && app.tagVariant ? (
          <span className={tagClassName[app.tagVariant]}>{app.tag}</span>
        ) : null}
      </div>
      {app.protected ? <LockIcon /> : null}
    </div>
    <p className="mt-2 flex-1 text-sm leading-6 text-slate-600">{app.description}</p>
    {!app.protected ? (
      <span className="mt-3 text-xs font-semibold uppercase tracking-wide text-teal-700">Public</span>
    ) : null}
  </>
);

export const NavCard = ({ app }: NavCardProps) => {
  if (app.url.startsWith("/")) {
    return (
      <Link href={app.url} className={cardClassName}>
        <NavCardContent app={app} />
      </Link>
    );
  }

  return (
    <a href={app.url} className={cardClassName}>
      <NavCardContent app={app} />
    </a>
  );
};
