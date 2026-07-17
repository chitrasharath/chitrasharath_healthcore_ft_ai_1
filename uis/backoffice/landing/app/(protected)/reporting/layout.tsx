import { ToolToolbar } from "@/components/layout/tool-toolbar";

export default function ReportingLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <>
      <ToolToolbar />
      {children}
    </>
  );
}
