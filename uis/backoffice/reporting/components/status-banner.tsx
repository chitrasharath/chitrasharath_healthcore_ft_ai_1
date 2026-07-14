type Props = { message: string; tone?: "error" | "info" };

export const StatusBanner = ({ message, tone = "error" }: Props) => (
  <div
    role="status"
    className={
      tone === "error"
        ? "rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
        : "rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900"
    }
  >
    {message}
  </div>
);
