type ErrorStateProps = {
  message: string;
  onRetry?: () => void;
};

export const ErrorState = ({ message, onRetry }: ErrorStateProps) => {
  return (
    <div className="px-4 py-6 text-sm" role="alert" aria-live="assertive">
      <p className="mb-2 text-[var(--hc-danger)]">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-md border border-[var(--hc-border)] px-3 py-1"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
};
