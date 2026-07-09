import { Router } from "express";

import { createRecoClient } from "../../lib/reco-client/factory.js";
import { ScaffoldDbSession } from "../../infrastructure/db/session.js";
import type { ApiLogger } from "../../infrastructure/logger/logger.js";
import type { RecoClient } from "../../infrastructure/reco-client/client.js";
import {
  createRecommendationApplicationService,
  type RecommendationApplicationService,
} from "./application-service.js";
import { createRecommendationController } from "./controller.js";
import { RecommendationRequestRepository } from "./request-repository.js";

export type RecommendationsRouterDeps = {
  applicationService?: RecommendationApplicationService;
  recoClient?: RecoClient;
  logger?: ApiLogger;
  dbSession?: ScaffoldDbSession;
};

function createDefaultApplicationService(
  deps: RecommendationsRouterDeps,
): RecommendationApplicationService {
  const recoClient =
    deps.recoClient ??
    createRecoClient({
      mode: "generated",
    });
  const dbSession = deps.dbSession ?? new ScaffoldDbSession();
  const requestRepository = new RecommendationRequestRepository({
    session: dbSession,
  });

  return createRecommendationApplicationService({
    recoClient,
    requestRepository,
    logger: deps.logger,
  });
}

/** POST /api/v1/recommendations を提供する Express Router。 */
export function createRecommendationsRouter(
  deps: RecommendationsRouterDeps = {},
): Router {
  const applicationService =
    deps.applicationService ?? createDefaultApplicationService(deps);
  const handler = createRecommendationController({
    applicationService,
    logger: deps.logger,
  });

  const router = Router();
  router.post("/", handler);

  return router;
}

export { createRecommendationsRouter as recommendationsRouter };
