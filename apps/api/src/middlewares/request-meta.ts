import { randomUUID } from "node:crypto";
import type { NextFunction, Request, Response } from "express";

import type { RequestMeta } from "./types.js";

const TRACE_HEADER = "x-trace-id";

function readTraceId(req: Request): string {
  const header = req.header(TRACE_HEADER);
  if (typeof header === "string" && header.trim().length > 0) {
    return header.trim();
  }
  return randomUUID();
}

function createRequestId(): string {
  return `req_${randomUUID().replace(/-/g, "").slice(0, 12)}`;
}

/** traceId / requestId を res.locals.apiMeta へ設定する。error handler の meta 生成に利用する。 */
export function requestMetaMiddleware(
  req: Request,
  res: Response,
  next: NextFunction,
): void {
  const meta: RequestMeta = {
    traceId: readTraceId(req),
    requestId: createRequestId(),
  };

  res.locals.apiMeta = meta;
  next();
}

export function resolveRequestMeta(res: Response): RequestMeta {
  return (
    res.locals.apiMeta ?? {
      traceId: randomUUID(),
      requestId: createRequestId(),
    }
  );
}
