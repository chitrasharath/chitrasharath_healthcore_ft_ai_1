import { ToolToolbar } from "@/components/layout/tool-toolbar";

export default function KnowledgeLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <>
      <ToolToolbar />
      {children}
    </>
  );
}
