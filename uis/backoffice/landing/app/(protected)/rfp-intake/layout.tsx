import { ToolToolbar } from "@/components/layout/tool-toolbar";

export default function RfpIntakeLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <>
      <ToolToolbar />
      {children}
    </>
  );
}
