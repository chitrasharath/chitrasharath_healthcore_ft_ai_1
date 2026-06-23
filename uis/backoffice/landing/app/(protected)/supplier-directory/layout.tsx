import { ToolToolbar } from "@/components/layout/tool-toolbar";

export default function SupplierDirectoryLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <>
      <ToolToolbar />
      {children}
    </>
  );
}
