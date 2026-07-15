import { Router } from "express";

import { createDbSession, type DbSession } from "../../infrastructure/db/index.js";
import type { ApiLogger } from "../../infrastructure/logger/logger.js";
import { createItemDetailController } from "./controller.js";
import { ItemDetailRepository } from "./repository.js";
import type { ItemDetailReader } from "./types.js";

export type ItemsRouterDeps = {
  reader?: ItemDetailReader;
  logger?: ApiLogger;
  dbSession?: DbSession;
  generatedAtFactory?: () => string;
};

function createDefaultReader(deps: ItemsRouterDeps): ItemDetailReader {
  return (
    deps.reader ??
    new ItemDetailRepository({
      session: deps.dbSession ?? createDbSession(),
    })
  );
}

/** GET /api/v1/items/:itemId を提供する Express Router（API-PUB-003）。 */
export function createItemsRouter(deps: ItemsRouterDeps = {}): Router {
  const reader = createDefaultReader(deps);
  const handler = createItemDetailController({
    reader,
    logger: deps.logger,
    generatedAtFactory: deps.generatedAtFactory,
  });

  const router = Router();
  router.get("/:itemId", handler);

  return router;
}
