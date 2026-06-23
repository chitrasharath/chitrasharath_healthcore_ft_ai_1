import { ToolToolbar } from "@/components/layout/tool-toolbar";

export default function BackofficeFunctionsLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <>
      <ToolToolbar />
      {children}
    </>
  );
}
