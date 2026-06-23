import { ToolToolbar } from "@/components/layout/tool-toolbar";

export default function IncidentAnalyzerLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <>
      <ToolToolbar />
      {children}
    </>
  );
}
