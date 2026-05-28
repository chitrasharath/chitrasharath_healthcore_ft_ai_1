import Link from "next/link";
import type { ReactNode } from "react";

type IconLinkProps = {
  href: string;
  label: string;
  icon: ReactNode;
  compact?: boolean;
};

export const IconLink = ({ href, label, icon, compact = true }: IconLinkProps) => {
  const mode = compact
    ? "h-8 w-8 justify-center"
    : "gap-2 px-2 py-1";

  return (
    <Link
      href={href}
      aria-label={label}
      className={`inline-flex items-center rounded-md border border-[var(--hc-border)] bg-white hover:bg-[var(--hc-surface-muted)] ${mode}`}
    >
      {icon}
      {compact ? <span className="sr-only">{label}</span> : <span>{label}</span>}
    </Link>
  );
};