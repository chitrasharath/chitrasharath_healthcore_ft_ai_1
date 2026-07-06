"use client";

import { usePathname } from "next/navigation";

import { useInventoryTimezone } from "@backoffice/inventory/components/inventory-timezone-context";
import { TimezoneSelect } from "@backoffice/inventory/components/timezone-select";
import { showsInventoryTime } from "@backoffice/inventory/lib/timezones";

export const InventoryTimezoneBar = () => {
  const pathname = usePathname();
  const { timezone, setTimezone } = useInventoryTimezone();

  if (!showsInventoryTime(pathname)) return null;

  return (
    <div className="mx-auto flex w-full max-w-5xl justify-end px-4 pt-4 sm:px-6">
      <TimezoneSelect value={timezone} onChange={setTimezone} />
    </div>
  );
};
