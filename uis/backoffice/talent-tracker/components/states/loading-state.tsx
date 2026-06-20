type LoadingStateProps = {
  message: string;
};

export const LoadingState = ({ message }: LoadingStateProps) => {
  return <p className="px-4 py-6 text-sm text-[var(--hc-text-muted)]">{message}</p>;
};
