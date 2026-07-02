import { ToolToolbar } from "@/components/layout/tool-toolbar";

import { InventoryLayoutShell } from "@backoffice/inventory/components/inventory-layout-shell";

export default function InventoryLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <>
      <ToolToolbar />
      <InventoryLayoutShell>{children}</InventoryLayoutShell>
    </>
  );
}
