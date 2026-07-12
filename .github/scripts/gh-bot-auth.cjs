"use strict";

const { execSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const DEFAULT_CONFIG_PATH = path.join(__dirname, "..", "ai-bot-account.json");

function nonEmpty(value) {
  return String(value || "").trim();
}

function expandHome(filePath) {
  const text = nonEmpty(filePath);
  if (!text.startsWith("~")) return text;
  return path.join(os.homedir(), text.slice(1).replace(/^[/\\]/, ""));
}

function loadBotAccountConfig(configPath = DEFAULT_CONFIG_PATH) {
  const resolved = path.resolve(configPath);
  if (!fs.existsSync(resolved)) {
    throw new Error(`Bot account config not found: ${resolved}`);
  }
  const config = JSON.parse(fs.readFileSync(resolved, "utf8"));
  const login = nonEmpty(config.machine_account_login);
  if (!login) {
    throw new Error("machine_account_login is required in ai-bot-account.json");
  }
  return {
    machineAccountLogin: login,
    humanReviewerLogin: nonEmpty(config.human_reviewer_login),
    tokenEnvVar: nonEmpty(config.token_env_var) || "GH_BOT_TOKEN",
    envFile: expandHome(config.env_file || "~/.config/gift-recommend/gh-bot.env"),
    repository: nonEmpty(config.repository),
    configPath: resolved,
  };
}

function parseEnvFile(content, tokenEnvVar) {
  const vars = {};
  for (const rawLine of String(content || "").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const exportMatch = /^export\s+([A-Za-z_][A-Za-z0-9_]*)=(.*)$/.exec(line);
    const plainMatch = /^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/.exec(line);
    const match = exportMatch || plainMatch;
    if (!match) continue;
    const key = match[1];
    let value = match[2].trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    vars[key] = value;
  }
  return vars[tokenEnvVar] || "";
}

function loadTokenFromEnvFile(envFile, tokenEnvVar) {
  if (!envFile || !fs.existsSync(envFile)) return "";
  return parseEnvFile(fs.readFileSync(envFile, "utf8"), tokenEnvVar);
}

function resolveBotToken({ config, tokenOverride } = {}) {
  const cfg = config || loadBotAccountConfig();
  const fromOverride = nonEmpty(tokenOverride);
  if (fromOverride) return fromOverride;
  const fromProcess = nonEmpty(process.env[cfg.tokenEnvVar]);
  if (fromProcess) return fromProcess;
  return loadTokenFromEnvFile(cfg.envFile, cfg.tokenEnvVar);
}

function resolveEffectiveGhToken() {
  return nonEmpty(process.env.GH_TOKEN) || nonEmpty(process.env.GITHUB_TOKEN);
}

function authHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
  };
}

async function fetchGitHubLogin({ token, fetchImpl }) {
  const send = fetchImpl || global.fetch;
  if (typeof send !== "function") {
    throw new Error("fetch is unavailable");
  }
  const response = await send("https://api.github.com/user", {
    headers: authHeaders(token),
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`GitHub API /user failed: HTTP ${response.status} ${text}`.trim());
  }
  const data = await response.json();
  return {
    login: nonEmpty(data.login),
    id: data.id,
  };
}

function fetchGhCliLogin({ ghExecImpl } = {}) {
  if (typeof ghExecImpl === "function") {
    return nonEmpty(ghExecImpl());
  }
  return nonEmpty(
    execSync("gh api user --jq .login", {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    }),
  );
}

async function verifyBotAuth({
  config,
  token,
  fetchImpl,
} = {}) {
  const cfg = config || loadBotAccountConfig();
  const resolvedToken = resolveBotToken({ config: cfg, tokenOverride: token });
  if (!resolvedToken) {
    return {
      ok: false,
      reason: "token_missing",
      message: `${cfg.tokenEnvVar} is not set. Create ${cfg.envFile} (see .github/gh-bot.env.example).`,
      config: cfg,
    };
  }

  let loginInfo;
  try {
    loginInfo = await fetchGitHubLogin({ token: resolvedToken, fetchImpl });
  } catch (error) {
    return {
      ok: false,
      reason: "api_error",
      message: error.message,
      config: cfg,
    };
  }

  if (loginInfo.login !== cfg.machineAccountLogin) {
    return {
      ok: false,
      reason: "wrong_login",
      message: `Expected machine account ${cfg.machineAccountLogin} but authenticated as ${loginInfo.login}. Use the bot Classic PAT, not the human account token.`,
      login: loginInfo.login,
      config: cfg,
    };
  }

  return {
    ok: true,
    login: loginInfo.login,
    id: loginInfo.id,
    token: resolvedToken,
    gitUser: {
      name: loginInfo.login,
      email: `${loginInfo.id}+${loginInfo.login}@users.noreply.github.com`,
    },
    config: cfg,
  };
}

function formatShellSetup(result) {
  const cfg = result.config;
  return [
    `# Machine account auth (${cfg.machineAccountLogin})`,
    `source ${cfg.envFile} 2>/dev/null || true`,
    `export GH_TOKEN="$${cfg.tokenEnvVar}"`,
    `export GITHUB_TOKEN="$${cfg.tokenEnvVar}"`,
    `# verify: gh api user --jq .login  # => ${cfg.machineAccountLogin}`,
  ].join("\n");
}

function formatHumanShellSetup(config) {
  const cfg = config || loadBotAccountConfig();
  const human = cfg.humanReviewerLogin || "human-reviewer";
  return [
    `# Human account auth (${human}) — temporary mode`,
    "unset GH_TOKEN",
    "unset GITHUB_TOKEN",
    `# verify: gh api user --jq .login  # => ${human}`,
  ].join("\n");
}

async function verifyHumanAuth({ config, ghExecImpl } = {}) {
  const cfg = config || loadBotAccountConfig();
  if (!cfg.humanReviewerLogin) {
    return {
      ok: false,
      reason: "human_reviewer_missing",
      message: "human_reviewer_login is not configured in ai-bot-account.json",
      config: cfg,
    };
  }

  if (resolveEffectiveGhToken()) {
    return {
      ok: false,
      reason: "bot_env_active",
      message:
        "GH_TOKEN / GITHUB_TOKEN is set. Run eval \"$(bash .github/scripts/gh-auth-mode.sh human)\" first.",
      config: cfg,
    };
  }

  let login;
  try {
    login = fetchGhCliLogin({ ghExecImpl });
  } catch (error) {
    return {
      ok: false,
      reason: "gh_cli_error",
      message: error.message || String(error),
      config: cfg,
    };
  }

  if (!login) {
    return {
      ok: false,
      reason: "gh_login_missing",
      message: "Could not resolve login from gh CLI. Run gh auth login as the human reviewer.",
      config: cfg,
    };
  }

  if (login !== cfg.humanReviewerLogin) {
    return {
      ok: false,
      reason: "wrong_login",
      message: `Expected human reviewer ${cfg.humanReviewerLogin} but gh authenticated as ${login}.`,
      login,
      config: cfg,
    };
  }

  return {
    ok: true,
    login,
    config: cfg,
  };
}

async function resolveAuthMode({ config, fetchImpl, ghExecImpl } = {}) {
  const cfg = config || loadBotAccountConfig();
  const effectiveToken = resolveEffectiveGhToken();

  if (effectiveToken) {
    let loginInfo;
    try {
      loginInfo = await fetchGitHubLogin({ token: effectiveToken, fetchImpl });
    } catch (error) {
      return {
        mode: "unknown",
        login: "",
        source: "env_token",
        message: error.message,
        config: cfg,
      };
    }

    if (loginInfo.login === cfg.machineAccountLogin) {
      return {
        mode: "bot",
        login: loginInfo.login,
        source: "env_token",
        config: cfg,
      };
    }

    return {
      mode: "unknown",
      login: loginInfo.login,
      source: "env_token",
      message: `GH_TOKEN is set but login is neither ${cfg.machineAccountLogin} nor ${cfg.humanReviewerLogin}.`,
      config: cfg,
    };
  }

  let login;
  try {
    login = fetchGhCliLogin({ ghExecImpl });
  } catch (error) {
    return {
      mode: "unknown",
      login: "",
      source: "gh_cli",
      message: error.message || String(error),
      config: cfg,
    };
  }

  if (login === cfg.humanReviewerLogin) {
    return {
      mode: "human",
      login,
      source: "gh_cli",
      config: cfg,
    };
  }

  if (login === cfg.machineAccountLogin) {
    return {
      mode: "unknown",
      login,
      source: "gh_cli",
      message: "Machine account detected via gh CLI without GH_TOKEN. Use print-setup for bot mode.",
      config: cfg,
    };
  }

  return {
    mode: "unknown",
    login,
    source: "gh_cli",
    message: `Unexpected gh login: ${login}`,
    config: cfg,
  };
}

function formatStatusLine(result) {
  const cfg = result.config;
  if (result.mode === "bot") {
    return `mode=bot login=${result.login} source=${result.source} (expected: ${cfg.machineAccountLogin})`;
  }
  if (result.mode === "human") {
    return `mode=human login=${result.login} source=${result.source} (expected: ${cfg.humanReviewerLogin})`;
  }
  const detail = result.message ? ` message=${result.message}` : "";
  return `mode=unknown login=${result.login || "n/a"} source=${result.source}${detail}`;
}

async function main(argv) {
  const args = argv.slice(2);
  const command = args[0] || "verify";

  if (command === "verify") {
    const result = await verifyBotAuth();
    if (!result.ok) {
      console.error(result.message);
      process.exit(1);
    }
    console.log(`OK: authenticated as ${result.login}`);
    if (result.config.humanReviewerLogin) {
      console.log(`Human Reviewer: ${result.config.humanReviewerLogin}`);
    }
    return;
  }

  if (command === "verify-human") {
    const result = await verifyHumanAuth();
    if (!result.ok) {
      console.error(result.message);
      process.exit(1);
    }
    console.log(`OK: human mode ready as ${result.login}`);
    return;
  }

  if (command === "print-setup") {
    const result = await verifyBotAuth();
    if (!result.ok) {
      console.error(result.message);
      process.exit(1);
    }
    console.log(formatShellSetup(result));
    return;
  }

  if (command === "print-human-setup") {
    const cfg = loadBotAccountConfig();
    console.log(formatHumanShellSetup(cfg));
    return;
  }

  if (command === "print-git-user") {
    const result = await verifyBotAuth();
    if (!result.ok) {
      console.error(result.message);
      process.exit(1);
    }
    console.log(JSON.stringify(result.gitUser));
    return;
  }

  if (command === "status") {
    const result = await resolveAuthMode();
    console.log(formatStatusLine(result));
    if (result.mode === "unknown") {
      process.exit(1);
    }
    return;
  }

  console.error(
    "Unknown command: " +
      command +
      ". Use verify | verify-human | print-setup | print-human-setup | print-git-user | status",
  );
  process.exit(1);
}

if (require.main === module) {
  main(process.argv).catch((error) => {
    console.error(error.message || error);
    process.exit(1);
  });
}

module.exports = {
  DEFAULT_CONFIG_PATH,
  loadBotAccountConfig,
  resolveBotToken,
  resolveEffectiveGhToken,
  verifyBotAuth,
  verifyHumanAuth,
  resolveAuthMode,
  formatShellSetup,
  formatHumanShellSetup,
  formatStatusLine,
  fetchGhCliLogin,
  expandHome,
};
