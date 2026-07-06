type StockBadgeProps = {
  stock: number;
};

const stockLevel = (stock: number): "low" | "warning" | "healthy" => {
  if (stock <= 5) return "low";
  if (stock <= 15) return "warning";
  return "healthy";
};

const levelClasses: Record<ReturnType<typeof stockLevel>, string> = {
  low: "rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-800",
  warning: "rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800",
  healthy: "rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-800",
};

export const StockBadge = ({ stock }: StockBadgeProps) => (
  <span className={levelClasses[stockLevel(stock)]}>{stock}</span>
);
