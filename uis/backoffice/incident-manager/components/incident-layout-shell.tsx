"use client";

import { IncidentTimezoneBar } from "@backoffice/incident-manager/components/incident-timezone-bar";
import { IncidentTimezoneProvider } from "@backoffice/incident-manager/components/incident-timezone-context";

export const IncidentLayoutShell = ({ children }: { children: React.ReactNode }) => (
  <IncidentTimezoneProvider>
    <IncidentTimezoneBar />
    {children}
  </IncidentTimezoneProvider>
);
