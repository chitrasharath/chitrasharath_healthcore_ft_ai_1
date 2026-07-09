import type { Config } from "jest";

const config: Config = {
  preset: "ts-jest",
  testEnvironment: "node",
  roots: ["<rootDir>/__tests__"],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
    "^@backoffice/shared/(.*)$": "<rootDir>/../shared/$1",
    "^@backoffice/inventory/(.*)$": "<rootDir>/../inventory/$1",
  },
};

export default config;
