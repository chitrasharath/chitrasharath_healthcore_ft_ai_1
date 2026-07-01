type StatusBannerProps = {
  variant: "success" | "error" | "warning";
  message: string;
};

const classes: Record<StatusBannerProps["variant"], string> = {
  success: "rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700",
  error: "rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700",
  warning: "rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700",
};

export const StatusBanner = ({ variant, message }: StatusBannerProps) => (
  <p className={classes[variant]} role="alert">
    {message}
  </p>
);
