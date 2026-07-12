import express, { type Express } from "express";

import { createHealthRouter } from "./app/health/routes.js";
import { createMastersRouter } from "./app/masters/index.js";
import { createRecommendationsRouter } from "./app/recommendations/index.js";
import {
  registerErrorMiddleware,
  registerFoundationMiddlewares,
} from "./middlewares/index.js";

/** Express アプリを組み立てる（listen は index 側）。 */
export function createApp(): Express {
  const app = express();

  registerFoundationMiddlewares(app);
  app.use("/api/v1", createHealthRouter());
  // API-PUB-002: POST /api/v1/recommendations（Router は "/" に POST を持つ）
  app.use("/api/v1/recommendations", createRecommendationsRouter());
  // API-PUB-006: GET /api/v1/masters/occasions（後続マスタも同一 Router）
  app.use("/api/v1/masters", createMastersRouter());
  registerErrorMiddleware(app);

  return app;
}
