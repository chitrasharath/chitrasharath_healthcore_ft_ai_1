"use client";

import { InventoryTimezoneBar } from "@backoffice/inventory/components/inventory-timezone-bar";
import { InventoryTimezoneProvider } from "@backoffice/inventory/components/inventory-timezone-context";

export const InventoryLayoutShell = ({ children }: { children: React.ReactNode }) => (
  <InventoryTimezoneProvider>
    <InventoryTimezoneBar />
    {children}
  </InventoryTimezoneProvider>
);
