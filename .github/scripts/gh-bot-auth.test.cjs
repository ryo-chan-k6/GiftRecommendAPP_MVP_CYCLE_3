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
  const previousBot = process.env.GH_BOT_TOKEN;
  delete process.env.GH_BOT_TOKEN;
  try {
    const result = await ghBotAuth.verifyBotAuth({
      config: { ...config, envFile: "/tmp/nonexistent-gh-bot.env", tokenEnvVar: "GH_BOT_TOKEN" },
      token: "",
      fetchImpl: async () => ({ ok: true, json: async () => ({ login: "okuri-ai-bot", id: 1 }) }),
    });
    assert.equal(result.ok, false);
    assert.equal(result.reason, "token_missing");
  } finally {
    if (previousBot === undefined) delete process.env.GH_BOT_TOKEN;
    else process.env.GH_BOT_TOKEN = previousBot;
  }
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

test("formatHumanShellSetup includes unset GH_TOKEN", () => {
  const config = ghBotAuth.loadBotAccountConfig();
  const setup = ghBotAuth.formatHumanShellSetup(config);
  assert.match(setup, /unset GH_TOKEN/);
  assert.match(setup, /unset GITHUB_TOKEN/);
  assert.match(setup, /ryo-chan-k6/);
});

test("resolveAuthMode returns bot when GH_TOKEN is machine account", async () => {
  const config = ghBotAuth.loadBotAccountConfig();
  const previousGh = process.env.GH_TOKEN;
  const previousGithub = process.env.GITHUB_TOKEN;
  process.env.GH_TOKEN = "ghp_test";
  delete process.env.GITHUB_TOKEN;
  try {
    const result = await ghBotAuth.resolveAuthMode({
      config,
      fetchImpl: async () => ({
        ok: true,
        json: async () => ({ login: "okuri-ai-bot", id: 99 }),
      }),
    });
    assert.equal(result.mode, "bot");
    assert.equal(result.login, "okuri-ai-bot");
    assert.equal(result.source, "env_token");
  } finally {
    if (previousGh === undefined) delete process.env.GH_TOKEN;
    else process.env.GH_TOKEN = previousGh;
    if (previousGithub === undefined) delete process.env.GITHUB_TOKEN;
    else process.env.GITHUB_TOKEN = previousGithub;
  }
});

test("resolveAuthMode returns human when gh CLI reports human reviewer", async () => {
  const config = ghBotAuth.loadBotAccountConfig();
  const previousGh = process.env.GH_TOKEN;
  const previousGithub = process.env.GITHUB_TOKEN;
  delete process.env.GH_TOKEN;
  delete process.env.GITHUB_TOKEN;
  try {
    const result = await ghBotAuth.resolveAuthMode({
      config,
      ghExecImpl: () => "ryo-chan-k6",
    });
    assert.equal(result.mode, "human");
    assert.equal(result.login, "ryo-chan-k6");
    assert.equal(result.source, "gh_cli");
  } finally {
    if (previousGh === undefined) delete process.env.GH_TOKEN;
    else process.env.GH_TOKEN = previousGh;
    if (previousGithub === undefined) delete process.env.GITHUB_TOKEN;
    else process.env.GITHUB_TOKEN = previousGithub;
  }
});

test("verifyHumanAuth fails when bot env is active", async () => {
  const config = ghBotAuth.loadBotAccountConfig();
  const previousGh = process.env.GH_TOKEN;
  process.env.GH_TOKEN = "ghp_test";
  try {
    const result = await ghBotAuth.verifyHumanAuth({ config });
    assert.equal(result.ok, false);
    assert.equal(result.reason, "bot_env_active");
  } finally {
    if (previousGh === undefined) delete process.env.GH_TOKEN;
    else process.env.GH_TOKEN = previousGh;
  }
});

test("verifyHumanAuth succeeds for configured human reviewer", async () => {
  const config = ghBotAuth.loadBotAccountConfig();
  const previousGh = process.env.GH_TOKEN;
  const previousGithub = process.env.GITHUB_TOKEN;
  delete process.env.GH_TOKEN;
  delete process.env.GITHUB_TOKEN;
  try {
    const result = await ghBotAuth.verifyHumanAuth({
      config,
      ghExecImpl: () => "ryo-chan-k6",
    });
    assert.equal(result.ok, true);
    assert.equal(result.login, "ryo-chan-k6");
  } finally {
    if (previousGh === undefined) delete process.env.GH_TOKEN;
    else process.env.GH_TOKEN = previousGh;
    if (previousGithub === undefined) delete process.env.GITHUB_TOKEN;
    else process.env.GITHUB_TOKEN = previousGithub;
  }
});
