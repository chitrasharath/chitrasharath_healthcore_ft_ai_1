import Link from "next/link";

const cardClassName =
  "group flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-sky-300 hover:shadow-md";

const INVENTORY_CARDS = [
  {
    title: "Supply Stock",
    description: "View all medical supplies and current stock levels",
    href: "/inventory/products",
  },
  {
    title: "Log Delivery",
    description: "Register an inbound supply delivery from a vendor",
    href: "/inventory/orders/inbound",
  },
  {
    title: "Log Consumption",
    description: "Record clinical use or waste of medical supplies",
    href: "/inventory/orders/outbound",
  },
  {
    title: "Order History",
    description: "View all supply deliveries and consumptions",
    href: "/inventory/orders",
  },
] as const;

export const InventoryNavCards = () => (
  <div className="mt-8 grid gap-4 sm:grid-cols-2">
    {INVENTORY_CARDS.map((card) => (
      <Link key={card.href} href={card.href} className={cardClassName}>
        <h3 className="font-semibold text-slate-900 group-hover:text-sky-800">{card.title}</h3>
        <p className="mt-2 flex-1 text-sm leading-6 text-slate-600">{card.description}</p>
      </Link>
    ))}
  </div>
);
