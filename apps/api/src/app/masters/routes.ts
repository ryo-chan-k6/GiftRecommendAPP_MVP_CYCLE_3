import { Router } from "express";

import {
  createDbSession,
  type DbSession,
} from "../../infrastructure/db/index.js";
import type { ApiLogger } from "../../infrastructure/logger/logger.js";
import { createOccasionController } from "./occasion-controller.js";
import { OccasionMasterRepository } from "./occasion-repository.js";

export type MastersRouterDeps = {
  dbSession?: DbSession;
  logger?: ApiLogger;
  occasionRepository?: OccasionMasterRepository;
  /** false で GRS-CFG-005。既定 true。 */
  mastersConfigResolved?: boolean;
};

/**
 * Public masters Router。
 * 本 Task（API-PUB-006）では GET /occasions のみ必須。
 * PUB-005 / 007 / 008 は同一 Router へ後続追加可。
 */
export function createMastersRouter(deps: MastersRouterDeps = {}): Router {
  const dbSession = deps.dbSession ?? createDbSession();
  const occasionRepository =
    deps.occasionRepository ??
    new OccasionMasterRepository({ session: dbSession });

  const getOccasions = createOccasionController({
    repository: occasionRepository,
    logger: deps.logger,
    mastersConfigResolved: deps.mastersConfigResolved,
  });

  const router = Router();
  router.get("/occasions", getOccasions);

  return router;
}
