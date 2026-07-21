import {
  GeneratedRecoClient,
  resolveRecoClientConfig,
  ScaffoldRecoClient,
  type GeneratedRecoClientOptions,
  type RecoClient,
  type RecoClientConfig,
  type ScaffoldRecoClientOptions,
} from "../../infrastructure/reco-client/index.js";

export type RecoClientFactoryMode = "generated" | "scaffold";

export type CreateRecoClientOptions = {
  mode?: RecoClientFactoryMode;
  config?: RecoClientConfig;
  env?: NodeJS.ProcessEnv;
  generated?: Omit<GeneratedRecoClientOptions, "config">;
  scaffold?: ScaffoldRecoClientOptions;
};

/** Create reco-client wrapper for apps/api DI boundaries. */
export function createRecoClient(
  options: CreateRecoClientOptions = {},
): RecoClient {
  const mode = options.mode ?? "generated";

  if (mode === "scaffold") {
    return new ScaffoldRecoClient(options.scaffold);
  }

  const config =
    options.config ?? resolveRecoClientConfig(options.env ?? process.env);

  return new GeneratedRecoClient({
    config,
    ...options.generated,
  });
}
