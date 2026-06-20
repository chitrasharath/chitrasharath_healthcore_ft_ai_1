import { ToolToolbar } from "@/components/layout/tool-toolbar";
import { Suspense } from "react";

import { StickyFooter } from "@backoffice/talent-tracker/components/sticky-footer";

export default function TalentTrackerLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <>
      <ToolToolbar />
      <div className="flex min-h-full flex-1 flex-col">
        <div className="flex-1 pb-16">{children}</div>
        <Suspense fallback={null}>
          <StickyFooter />
        </Suspense>
      </div>
    </>
  );
}
