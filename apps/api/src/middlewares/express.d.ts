import type { RequestMeta } from "./types.js";

declare global {
  namespace Express {
    interface Locals {
      apiMeta?: RequestMeta;
    }
  }
}

export {};
