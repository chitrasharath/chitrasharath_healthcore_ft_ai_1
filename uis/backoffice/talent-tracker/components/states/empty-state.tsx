type EmptyStateProps = {
  message: string;
};

export const EmptyState = ({ message }: EmptyStateProps) => {
  return <p className="px-4 py-6 text-sm text-[var(--hc-text-muted)]">{message}</p>;
};
