import path from "path";
import type { NextConfig } from "next";

const repoRoot = path.join(__dirname, "../..");

const nextConfig: NextConfig = {
  experimental: {
    externalDir: true,
  },
  turbopack: {
    root: repoRoot,
    resolveAlias: {
      "@healthcore/src": path.join(repoRoot, "apps/src"),
    },
  },
  webpack: (config) => {
    config.resolve ??= {};
    config.resolve.extensionAlias = {
      ".js": [".ts", ".tsx", ".js"],
      ".jsx": [".tsx", ".jsx"],
    };
    return config;
  },
};

export default nextConfig;
