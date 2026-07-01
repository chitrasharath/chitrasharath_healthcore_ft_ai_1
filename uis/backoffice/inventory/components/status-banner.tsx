type StatusBannerProps = {
  variant: "success" | "error" | "warning";
  message: string;
};

const variantClasses: Record<StatusBannerProps["variant"], string> = {
  success: "rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800",
  error: "rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800",
  warning: "rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800",
};

export const StatusBanner = ({ variant, message }: StatusBannerProps) => (
  <p className={variantClasses[variant]} role="alert">
    {message}
  </p>
);
