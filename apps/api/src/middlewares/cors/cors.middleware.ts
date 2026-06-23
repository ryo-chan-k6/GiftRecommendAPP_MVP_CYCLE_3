import type { NextFunction, Request, Response } from "express";

import { DEFAULT_CORS_ORIGIN } from "../constants.js";

export interface CorsMiddlewareOptions {
  allowedOrigins?: readonly string[];
  allowMethods?: readonly string[];
  allowHeaders?: readonly string[];
}

const DEFAULT_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"] as const;
const DEFAULT_HEADERS = [
  "Content-Type",
  "Authorization",
  "X-Trace-Id",
  "X-Request-Id",
] as const;

function parseAllowedOrigins(raw: string | undefined): readonly string[] {
  if (raw === undefined || raw.trim().length === 0) {
    return [DEFAULT_CORS_ORIGIN];
  }

  return raw
    .split(",")
    .map((origin) => origin.trim())
    .filter((origin) => origin.length > 0);
}

function resolveAllowedOrigins(options?: CorsMiddlewareOptions): readonly string[] {
  if (options?.allowedOrigins !== undefined && options.allowedOrigins.length > 0) {
    return options.allowedOrigins;
  }

  return parseAllowedOrigins(process.env.CORS_ALLOWED_ORIGINS);
}

function isOriginAllowed(origin: string | undefined, allowedOrigins: readonly string[]): boolean {
  if (origin === undefined) {
    return true;
  }

  return allowedOrigins.includes(origin);
}

/** MVP CORS 骨格。許可 Origin は CORS_ALLOWED_ORIGINS（環境設計書 §19.5）を正とする。 */
export function createCorsMiddleware(options?: CorsMiddlewareOptions) {
  const allowedOrigins = resolveAllowedOrigins(options);
  const allowMethods = options?.allowMethods ?? DEFAULT_METHODS;
  const allowHeaders = options?.allowHeaders ?? DEFAULT_HEADERS;

  return function corsMiddleware(req: Request, res: Response, next: NextFunction): void {
    const origin = req.header("Origin");

    if (isOriginAllowed(origin, allowedOrigins) && origin !== undefined) {
      res.setHeader("Access-Control-Allow-Origin", origin);
      res.setHeader("Vary", "Origin");
    }

    res.setHeader("Access-Control-Allow-Methods", allowMethods.join(", "));
    res.setHeader("Access-Control-Allow-Headers", allowHeaders.join(", "));

    if (req.method === "OPTIONS") {
      res.status(204).end();
      return;
    }

    next();
  };
}

export { parseAllowedOrigins };
