type EmptyStateProps = {
  message: string;
};

export const EmptyState = ({ message }: EmptyStateProps) => (
  <p className="py-12 text-center text-sm text-slate-500">{message}</p>
);
