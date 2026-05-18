import fs from "node:fs";
import path from "node:path";

const appRoot = process.cwd();
const envPath = path.join(appRoot, ".env.local");
const reportPath = path.join(appRoot, "docs", "api-smoke-check.md");

const readEnvVar = (key) => {
  if (process.env[key]) return process.env[key];
  if (!fs.existsSync(envPath)) return "";

  const line = fs
    .readFileSync(envPath, "utf8")
    .split("\n")
    .find((item) => item.trim().startsWith(`${key}=`));

  return line ? line.split("=").slice(1).join("=").trim() : "";
};

const baseUrl = readEnvVar("NEXT_PUBLIC_API_URL");
if (!baseUrl) {
  throw new Error("Missing NEXT_PUBLIC_API_URL in environment.");
}

const request = async ({ method, url, body }) => {
  try {
    const response = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });

    return {
      reachable: true,
      status: response.status,
      ok: response.ok,
      note: response.ok ? "ok" : "non-2xx but reachable",
    };
  } catch (error) {
    return {
      reachable: false,
      status: 0,
      ok: false,
      note: error instanceof Error ? error.message : "network error",
    };
  }
};

const listResult = await request({ method: "GET", url: `${baseUrl}/records?page=1&limit=2` });
let validId = "unknown-id";

if (listResult.reachable && listResult.status === 200) {
  const listResponse = await fetch(`${baseUrl}/records?page=1&limit=2`);
  const listJson = await listResponse.json();
  validId = listJson?.data?.[0]?.id ?? "unknown-id";
}

const checks = [
  { name: "GET /records", method: "GET", url: `${baseUrl}/records?page=1&limit=2` },
  { name: "GET /records/{id}", method: "GET", url: `${baseUrl}/records/${validId}` },
  { name: "POST /records", method: "POST", url: `${baseUrl}/records`, body: {} },
  { name: "PUT /records/{id}", method: "PUT", url: `${baseUrl}/records/invalid-id`, body: {} },
  { name: "PATCH /records/{id}", method: "PATCH", url: `${baseUrl}/records/invalid-id`, body: { status: "received" } },
  { name: "DELETE /records/{id}", method: "DELETE", url: `${baseUrl}/records/invalid-id` },
  { name: "GET /records/{id}/notes", method: "GET", url: `${baseUrl}/records/${validId}/notes` },
  { name: "POST /records/{id}/notes", method: "POST", url: `${baseUrl}/records/invalid-id/notes`, body: { content: "smoke-check" } },
  { name: "DELETE /records/{id}/notes/{note_id}", method: "DELETE", url: `${baseUrl}/records/invalid-id/notes/invalid-note` },
];

const results = [];
for (const check of checks) {
  results.push({ ...check, ...(await request(check)) });
}

const markdown = [
  "# API Smoke Check",
  "",
  `- Executed at: ${new Date().toISOString()}`,
  `- Base URL: ${baseUrl}`,
  `- Strategy: mutating endpoints tested with invalid IDs or invalid payloads to confirm reachability without updating real records.`,
  "",
  "| Endpoint | Method | Status | Reachable | Note |",
  "|---|---|---:|---|---|",
  ...results.map(
    (row) =>
      `| ${row.name} | ${row.method} | ${row.status} | ${row.reachable ? "yes" : "no"} | ${row.note} |`,
  ),
  "",
  "## Mismatch Notes",
  "- POST /records with empty payload is expected to fail validation; a non-2xx response here still confirms route reachability.",
  "- PATCH and PUT were checked with invalid IDs to avoid side effects.",
];

fs.writeFileSync(reportPath, markdown.join("\n"));
console.log(`Smoke check report written: ${reportPath}`);
