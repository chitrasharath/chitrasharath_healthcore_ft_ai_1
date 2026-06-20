import path from "path";
import type { NextConfig } from "next";

const landingDir = __dirname;
const repoRoot = path.join(landingDir, "../../..");
const backofficeFunctions = path.join(landingDir, "../backoffice_functions");
const incidentAnalyzer = path.join(repoRoot, "uis/incident_analyzer");
const supplierDirectory = path.join(repoRoot, "uis/supplier_directory");
const talentTracker = path.join(landingDir, "../talent-tracker");
const backofficeShared = path.join(landingDir, "../shared");
const appsSrc = path.join(repoRoot, "apps/src");

const featureAliases = {
  "@backoffice/backoffice-functions": backofficeFunctions,
  "@backoffice/incident-analyzer": incidentAnalyzer,
  "@backoffice/supplier-directory": supplierDirectory,
  "@backoffice/talent-tracker": talentTracker,
  "@backoffice/shared": backofficeShared,
  "@healthcore/src": appsSrc,
};

const nextConfig: NextConfig = {
  experimental: {
    externalDir: true,
  },
  async redirects() {
    return [{ source: "/favicon.ico", destination: "/icon", permanent: false }];
  },
  turbopack: {
    root: repoRoot,
    resolveAlias: featureAliases,
  },
  webpack: (config) => {
    config.resolve ??= {};
    config.resolve.alias = {
      ...config.resolve.alias,
      ...featureAliases,
    };
    config.resolve.extensionAlias = {
      ".js": [".ts", ".tsx", ".js"],
      ".jsx": [".tsx", ".jsx"],
    };
    return config;
  },
};

export default nextConfig;
