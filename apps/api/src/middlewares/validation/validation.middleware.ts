import type { NextFunction, Request, Response } from "express";
import type { ZodType } from "zod";
import { ZodError } from "zod";

import type { ErrorDetail } from "../types.js";
import { createValidationApiError } from "../error/error.middleware.js";

export type ValidationSource = "body" | "query" | "params";

function mapZodIssues(error: ZodError): ErrorDetail[] {
  return error.issues.map((issue) => ({
    field: issue.path.length > 0 ? issue.path.join(".") : "_root",
    message: issue.message,
  }));
}

/** Zod schema による request validation 骨格。失敗時は ApiError を next へ渡す。 */
export function createValidationMiddleware<T>(
  schema: ZodType<T>,
  source: ValidationSource,
) {
  return function validationMiddleware(
    req: Request,
    _res: Response,
    next: NextFunction,
  ): void {
    const result = schema.safeParse(req[source]);

    if (!result.success) {
      next(createValidationApiError(mapZodIssues(result.error)));
      return;
    }

    req[source] = result.data;
    next();
  };
}

export { mapZodIssues };
