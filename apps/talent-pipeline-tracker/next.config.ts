import type { NextConfig } from "next";
import fs from "node:fs";
import path from "node:path";

const getEnvLocalValue = (key: string): string | undefined => {
  const envLocalPath = path.join(process.cwd(), ".env.local");

  if (!fs.existsSync(envLocalPath)) return undefined;

  const lines = fs.readFileSync(envLocalPath, "utf8").split("\n");
  const entry = lines.find((line) => {
    const trimmed = line.trim();
    return trimmed.length > 0 && !trimmed.startsWith("#") && trimmed.startsWith(`${key}=`);
  });

  return entry ? entry.slice(key.length + 1).trim() : undefined;
};

const apiUrlFromEnvLocal = getEnvLocalValue("NEXT_PUBLIC_API_URL");

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: apiUrlFromEnvLocal,
  },
};

export default nextConfig;
