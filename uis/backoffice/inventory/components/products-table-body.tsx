import Link from "next/link";

import { StockBadge } from "@backoffice/inventory/components/stock-badge";
import { formatCategoryLabel } from "@backoffice/inventory/lib/format";
import type { MedicalSupply } from "@backoffice/inventory/types/inventory";

type ProductsTableBodyProps = {
  products: MedicalSupply[];
};

export const ProductsTableBody = ({ products }: ProductsTableBodyProps) => (
  <tbody className="divide-y divide-slate-100">
    {products.map((product) => (
      <tr key={product.id} className="hover:bg-slate-50">
        <td className="px-4 py-3 font-medium text-slate-900">{product.name}</td>
        <td className="px-4 py-3 text-slate-700">{product.sku}</td>
        <td className="px-4 py-3 text-slate-700">{formatCategoryLabel(product.category)}</td>
        <td className="px-4 py-3 text-slate-700">{product.unit}</td>
        <td className="px-4 py-3 text-slate-700">{product.country}</td>
        <td className="px-4 py-3">
          <StockBadge stock={product.current_stock} />
        </td>
        <td className="px-4 py-3">
          <div className="flex flex-wrap gap-2">
            <Link
              href={`/inventory/orders/inbound?supplyId=${product.id}`}
              className="text-sm font-semibold text-sky-800 hover:underline"
            >
              Log Delivery
            </Link>
            <Link
              href={`/inventory/orders/outbound?supplyId=${product.id}`}
              className="text-sm font-semibold text-sky-800 hover:underline"
            >
              Log Consumption
            </Link>
          </div>
        </td>
      </tr>
    ))}
  </tbody>
);
