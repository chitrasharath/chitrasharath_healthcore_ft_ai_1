import { OrderTypeBadge } from "@backoffice/inventory/components/order-type-badge";
import {
  formatClinicName,
  formatConsumptionType,
  formatOrderDate,
} from "@backoffice/inventory/lib/format";
import type { OrderRead } from "@backoffice/inventory/types/inventory";

type OrdersTableBodyProps = {
  orders: OrderRead[];
  timeZone: string;
};

const orderDetail = (order: OrderRead): string => {
  if (order.order_type === "inbound") return order.vendor_name ?? "—";
  return formatConsumptionType(order.consumption_type);
};

export const OrdersTableBody = ({ orders, timeZone }: OrdersTableBodyProps) => (
  <tbody className="divide-y divide-slate-100">
    {orders.map((order) => (
      <tr key={`${order.order_type}-${order.id}`} className="hover:bg-slate-50">
        <td className="px-4 py-3">
          <div className="font-medium text-slate-900">{order.supply_name}</div>
          <div className="text-xs text-slate-500">{orderDetail(order)}</div>
        </td>
        <td className="px-4 py-3 text-slate-700">{order.quantity}</td>
        <td className="px-4 py-3">
          <OrderTypeBadge orderType={order.order_type} />
        </td>
        <td className="px-4 py-3 text-slate-700">{formatClinicName(order.clinic_id)}</td>
        <td className="px-4 py-3 text-slate-700">{formatOrderDate(order.created_at, timeZone)}</td>
        <td className="px-4 py-3 font-mono text-xs text-slate-600">{order.user_uuid}</td>
      </tr>
    ))}
  </tbody>
);
