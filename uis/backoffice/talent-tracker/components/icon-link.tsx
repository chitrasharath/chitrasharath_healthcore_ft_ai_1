import Link from "next/link";
import type { ReactNode } from "react";

type IconLinkProps = {
  href: string;
  label: string;
  icon: ReactNode;
  compact?: boolean;
};

const iconWrapClass = "inline-flex h-4 w-4 shrink-0 items-center justify-center [&_svg]:h-4 [&_svg]:w-4";

export const IconLink = ({ href, label, icon, compact = true }: IconLinkProps) => {
  const sizeClass = compact ? "h-8 w-8 justify-center p-0" : "gap-2 px-2.5 py-1.5";

  return (
    <Link
      href={href}
      aria-label={label}
      title={label}
      className={`inline-flex items-center rounded-lg border border-slate-300 bg-white text-slate-700 transition hover:bg-slate-50 ${sizeClass}`}
    >
      <span className={iconWrapClass} aria-hidden="true">
        {icon}
      </span>
      {!compact ? <span className="text-sm font-medium">{label}</span> : null}
    </Link>
  );
};
