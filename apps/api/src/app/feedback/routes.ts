import { Router } from "express";

import { createDbSession, type DbSession } from "../../infrastructure/db/index.js";
import type { ApiLogger } from "../../infrastructure/logger/logger.js";
import { createFeedbackController } from "./controller.js";
import { FeedbackRepository } from "./repository.js";
import { createFeedbackService, type FeedbackService } from "./service.js";

export type FeedbackRouterDeps = {
  service?: FeedbackService;
  repository?: FeedbackRepository;
  logger?: ApiLogger;
  dbSession?: DbSession;
};

function createDefaultService(deps: FeedbackRouterDeps): FeedbackService {
  const repository =
    deps.repository ??
    new FeedbackRepository({
      session: deps.dbSession ?? createDbSession(),
    });

  return createFeedbackService({ repository });
}

/** POST /api/v1/recommendation-results/:resultId/feedback を提供する Express Router。 */
export function createFeedbackRouter(deps: FeedbackRouterDeps = {}): Router {
  const service = deps.service ?? createDefaultService(deps);
  const handler = createFeedbackController({
    service,
    logger: deps.logger,
  });

  const router = Router();
  router.post("/:resultId/feedback", handler);

  return router;
}
