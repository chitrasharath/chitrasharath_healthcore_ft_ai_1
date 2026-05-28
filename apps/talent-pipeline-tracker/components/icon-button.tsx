import type { ButtonHTMLAttributes, ReactNode } from "react";

type IconButtonProps = {
  label: string;
  icon: ReactNode;
  compact?: boolean;
} & ButtonHTMLAttributes<HTMLButtonElement>;

export const IconButton = ({
  label,
  icon,
  compact = true,
  className = "",
  ...buttonProps
}: IconButtonProps) => {
  const mode = compact ? "h-8 w-8 justify-center" : "px-3 py-2";

  return (
    <button
      {...buttonProps}
      aria-label={label}
      className={`inline-flex items-center gap-2 rounded-md border border-[var(--hc-border)] bg-white text-sm text-[var(--hc-text)] hover:bg-[var(--hc-surface-muted)] ${mode} ${className}`}
    >
      <span className="h-4 w-4">{icon}</span>
      {compact ? <span className="sr-only">{label}</span> : <span>{label}</span>}
    </button>
  );
};