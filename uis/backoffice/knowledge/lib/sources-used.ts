/** Human-readable labels for agent `sources_used` values. */

const TOOL_LABELS: Record<string, string> = {
  rag: "Knowledge base",
  incident_tool: "Incident tool (MCP)",
  inventory_tool: "Inventory tool (MCP)",
};

export function formatSourcesUsed(sourcesUsed: string[] | undefined): string[] {
  if (!sourcesUsed?.length) return [];
  return sourcesUsed.map((id) => TOOL_LABELS[id] ?? id);
}
