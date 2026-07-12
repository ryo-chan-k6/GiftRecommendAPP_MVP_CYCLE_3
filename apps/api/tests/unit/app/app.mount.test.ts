import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { test } from "node:test";

import { createApp } from "../../../src/app.js";

async function withAppServer(
  run: (baseUrl: string) => Promise<void>,
): Promise<void> {
  const app = createApp();
  const server = app.listen(0);
  try {
    const address = server.address() as AddressInfo;
    await run(`http://127.0.0.1:${address.port}`);
  } finally {
    await new Promise<void>((resolve, reject) => {
      server.close((error: Error | undefined) =>
        error ? reject(error) : resolve(),
      );
    });
  }
}

test("GET /api/v1/health returns 200 after recommendations mount", async () => {
  await withAppServer(async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/health`);
    assert.equal(response.status, 200);
    const body = (await response.json()) as { data?: { status?: string } };
    assert.equal(body.data?.status, "ok");
  });
});

test("POST /api/v1/recommendations is mounted (not 404)", async () => {
  await withAppServer(async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/recommendations`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        relationship: { relationshipCode: "boss" },
        occasion: { occasionCode: "thanks" },
        execution: { mode: "ui" },
      }),
    });
    // マウント確認が目的。Validation / scaffold / reco 失敗は 404 以外で可。
    assert.notEqual(response.status, 404);
  });
});

test("GET /api/v1/masters/relationships is mounted (not 404)", async () => {
  await withAppServer(async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/masters/relationships`);
    // DATABASE_URL 未設定時は設定解決不能で 500 になり得る。404 でないことのみ確認。
    assert.notEqual(response.status, 404);
  });
});

test("GET /api/v1/masters/occasions is mounted (200 empty on scaffold)", async () => {
  await withAppServer(async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/v1/masters/occasions`, {
      headers: { Accept: "application/json" },
    });
    assert.equal(response.status, 200);
    const body = (await response.json()) as {
      data?: { occasions?: unknown[] };
      meta?: { count?: number };
    };
    assert.ok(Array.isArray(body.data?.occasions));
    assert.equal(body.meta?.count, body.data?.occasions?.length);
  });
});
