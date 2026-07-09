import type { Express } from "express";

import { createCorsMiddleware } from "./cors/index.js";
import { errorHandler } from "./error/index.js";
import { requestMetaMiddleware } from "./request-meta.js";

export * from "./constants.js";
export * from "./cors/index.js";
export * from "./error/index.js";
export * from "./request-meta.js";
export * from "./types.js";
export * from "./validation/index.js";

/**
 * Phase4a 共通 middleware の推奨登録順。
 * errorHandler は routes 登録後に必ず末尾へ配置する。
 */
export function registerFoundationMiddlewares(app: Express): void {
  app.use(requestMetaMiddleware);
  app.use(createCorsMiddleware());
}

export function registerErrorMiddleware(app: Express): void {
  app.use(errorHandler);
}
