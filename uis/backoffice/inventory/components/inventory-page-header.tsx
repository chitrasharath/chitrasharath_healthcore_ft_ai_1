import Link from "next/link";

type InventoryPageHeaderProps = {
  title: string;
  subtitle?: string;
};

export const InventoryPageHeader = ({ title, subtitle }: InventoryPageHeaderProps) => (
  <header className="mb-6">
    <Link href="/inventory" className="text-sm font-semibold text-sky-800 hover:text-sky-950">
      ← Back to Inventory
    </Link>
    <h1 className="mt-2 text-xl font-bold text-slate-900">{title}</h1>
    {subtitle ? <p className="mt-1 text-sm text-slate-600">{subtitle}</p> : null}
  </header>
);
