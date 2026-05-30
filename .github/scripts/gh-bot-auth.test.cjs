"use strict";

const assert = require("node:assert/strict");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { test } = require("node:test");

const ghBotAuth = require("./gh-bot-auth.cjs");

test("expandHome expands tilde path", () => {
  assert.match(ghBotAuth.expandHome("~/foo/bar"), new RegExp(`${os.homedir()}[/\\\\]foo[/\\\\]bar$`));
});

test("loadBotAccountConfig reads machine account login", () => {
  const config = ghBotAuth.loadBotAccountConfig();
  assert.equal(config.machineAccountLogin, "okuri-ai-bot");
  assert.equal(config.humanReviewerLogin, "ryo-chan-k6");
});

test("resolveBotToken prefers explicit override", () => {
  const config = ghBotAuth.loadBotAccountConfig();
  assert.equal(ghBotAuth.resolveBotToken({ config, tokenOverride: "ghp_test" }), "ghp_test");
});

test("verifyBotAuth fails when token missing", async () => {
  const config = ghBotAuth.loadBotAccountConfig();
  const result = await ghBotAuth.verifyBotAuth({
    config: { ...config, envFile: "/tmp/nonexistent-gh-bot.env", tokenEnvVar: "GH_BOT_TOKEN" },
    token: "",
    fetchImpl: async () => ({ ok: true, json: async () => ({ login: "okuri-ai-bot", id: 1 }) }),
  });
  assert.equal(result.ok, false);
  assert.equal(result.reason, "token_missing");
});

test("verifyBotAuth fails on wrong login", async () => {
  const config = ghBotAuth.loadBotAccountConfig();
  const result = await ghBotAuth.verifyBotAuth({
    config,
    token: "ghp_test",
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({ login: "ryo-chan-k6", id: 2 }),
    }),
  });
  assert.equal(result.ok, false);
  assert.equal(result.reason, "wrong_login");
});

test("verifyBotAuth succeeds for configured machine account", async () => {
  const config = ghBotAuth.loadBotAccountConfig();
  const result = await ghBotAuth.verifyBotAuth({
    config,
    token: "ghp_test",
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({ login: "okuri-ai-bot", id: 99 }),
    }),
  });
  assert.equal(result.ok, true);
  assert.equal(result.login, "okuri-ai-bot");
  assert.equal(result.gitUser.email, "99+okuri-ai-bot@users.noreply.github.com");
});

test("resolveBotToken reads env file", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "gh-bot-env-"));
  const envFile = path.join(dir, "gh-bot.env");
  fs.writeFileSync(envFile, 'export GH_BOT_TOKEN="ghp_from_file"\n', "utf8");
  const config = {
    ...ghBotAuth.loadBotAccountConfig(),
    envFile,
    tokenEnvVar: "GH_BOT_TOKEN",
  };
  const previous = process.env.GH_BOT_TOKEN;
  delete process.env.GH_BOT_TOKEN;
  try {
    assert.equal(ghBotAuth.resolveBotToken({ config }), "ghp_from_file");
  } finally {
    if (previous === undefined) delete process.env.GH_BOT_TOKEN;
    else process.env.GH_BOT_TOKEN = previous;
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
