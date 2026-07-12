import { Router, type Request, type Response } from "express";

import { resolveRequestMeta } from "../../middlewares/request-meta.js";

/**
 * API-PUB-001: GET /api/v1/health
 * 契約正本: packages/contracts/openapi/public-api.yaml
 * MVP: プロセス稼働確認。依存詳細は表面化しない。
 */
export function createHealthRouter(): Router {
  const router = Router();

  router.get("/health", (_req: Request, res: Response) => {
    const meta = resolveRequestMeta(res);
    const checkedAt = new Date().toISOString();

    res.status(200).json({
      data: {
        status: "ok",
        service: "okuri",
        apiVersion: "v1",
        checkedAt,
      },
      meta: {
        traceId: meta.traceId,
        requestId: meta.requestId,
        generatedAt: checkedAt,
      },
    });
  });

  return router;
}
