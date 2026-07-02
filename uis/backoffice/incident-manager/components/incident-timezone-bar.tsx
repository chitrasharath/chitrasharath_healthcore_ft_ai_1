"use client";

import { usePathname } from "next/navigation";

import { useIncidentTimezone } from "@backoffice/incident-manager/components/incident-timezone-context";
import { TimezoneSelect } from "@backoffice/incident-manager/components/timezone-select";
import { showsIncidentTime } from "@backoffice/incident-manager/lib/timezones";

export const IncidentTimezoneBar = () => {
  const pathname = usePathname();
  const { timezone, setTimezone } = useIncidentTimezone();

  if (!showsIncidentTime(pathname)) return null;

  return (
    <div className="mx-auto flex w-full max-w-7xl justify-end px-4 pt-4 sm:px-6 lg:px-8">
      <TimezoneSelect value={timezone} onChange={setTimezone} />
    </div>
  );
};
