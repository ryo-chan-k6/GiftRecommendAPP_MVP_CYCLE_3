# bot author Human Review E2E

## 目的

`okuri-ai-bot`（machine account）の Classic PAT で PR を open し、`ryo-chan-k6` が Human Review（Approve / Request changes）できることを確認する。

正本設定: `.github/ai-bot-account.json`

## 手順

1. bot PAT（`GH_BOT_TOKEN`）で branch push
2. `gh pr create`（author = `okuri-ai-bot`）
3. `ryo-chan-k6` で PR を開き Review changes → Approve / Request changes が選べること

## 再実行

```bash
node .github/scripts/gh-bot-auth.cjs verify
bash .github/scripts/e2e-bot-author-test-pr.sh
```

## 後片付け

検証後、この PR は Close してよい（merge 不要）。

## 関連

- [AI機械アカウント運用設計書](../../docs/00_共通/AIエージェント運用/AI機械アカウント運用設計書.md)
