import { ToolToolbar } from "@/components/layout/tool-toolbar";

import { IncidentLayoutShell } from "@backoffice/incident-manager/components/incident-layout-shell";

export default function IncidentManagerLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <>
      <ToolToolbar />
      <IncidentLayoutShell>{children}</IncidentLayoutShell>
    </>
  );
}
