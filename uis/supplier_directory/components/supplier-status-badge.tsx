type SupplierStatusBadgeProps = {
  status: "active" | "suspended";
};

export const SupplierStatusBadge = ({ status }: SupplierStatusBadgeProps) => {
  const isActive = status === "active";
  return (
    <span
      className={
        isActive
          ? "inline-flex rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800"
          : "inline-flex rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-900"
      }
    >
      {isActive ? "Active" : "Suspended"}
    </span>
  );
};
