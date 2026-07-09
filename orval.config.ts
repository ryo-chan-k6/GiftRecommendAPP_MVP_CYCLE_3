import { defineConfig } from "orval";

/**
 * Orval 設定正本（リポジトリルート）。
 * - publicApi: web → api（API-PUB-002）— bundler 向け既定出力
 * - internalRecoApi: api → reco（API-INT-002）— NodeNext + recoFetch mutator
 */
export default defineConfig({
  publicApi: {
    input: "./packages/contracts/openapi/public-api.yaml",
    output: {
      target: "./apps/web/src/generated/api",
      client: "fetch",
      mode: "tags-split",
      clean: true,
    },
  },
  internalRecoApi: {
    input: "./packages/contracts/openapi/internal-reco-api.yaml",
    output: {
      target: "./apps/api/src/generated/reco-client",
      client: "fetch",
      mode: "tags-split",
      clean: true,
      tsconfig: "./apps/api/tsconfig.orval.json",
      override: {
        mutator: {
          path: "./apps/api/src/infrastructure/reco-client/orval-mutator.ts",
          name: "recoFetch",
        },
      },
    },
  },
});
