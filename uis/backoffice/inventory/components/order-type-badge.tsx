type OrderTypeBadgeProps = {
  orderType: "inbound" | "outbound";
};

export const OrderTypeBadge = ({ orderType }: OrderTypeBadgeProps) => {
  if (orderType === "inbound") {
    return (
      <span className="rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-800">
        Delivery
      </span>
    );
  }
  return (
    <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-800">
      Consumption
    </span>
  );
};
