import express, { type Express } from "express";

import { createHealthRouter } from "./app/health/routes.js";
import {
  registerErrorMiddleware,
  registerFoundationMiddlewares,
} from "./middlewares/index.js";

/** Express アプリを組み立てる（listen は index 側）。 */
export function createApp(): Express {
  const app = express();

  registerFoundationMiddlewares(app);
  app.use("/api/v1", createHealthRouter());
  registerErrorMiddleware(app);

  return app;
}
