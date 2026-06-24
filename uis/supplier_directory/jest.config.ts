import type { Config } from "jest";

const config: Config = {
  preset: "ts-jest",
  testEnvironment: "node",
  roots: ["<rootDir>/__tests__"],
  moduleNameMapper: {
    "^@backoffice/supplier-directory/(.*)$": "<rootDir>/$1",
  },
  collectCoverageFrom: ["lib/**/*.ts"],
};

export default config;
