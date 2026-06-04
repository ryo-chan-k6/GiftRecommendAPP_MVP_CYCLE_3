# AI機械アカウント（Machine Account）運用設計書

## 1. 目的

MVP Cycle 3 の AI 主導開発において、**Human Review**（GitHub PR Review の Approve / Request changes）を人間（`ryo-chan-k6`）が実施できるよう、GitHub 上の **PR author** と **Human Reviewer** を分離する。

GitHub は PR author 自身に Approve / Request changes を許可しない。AI Agent が人間アカウントの `gh` 認証で PR を open すると author が人間になり、Human Review 正式経路（`changes_requested` → Projects `In Progress`）が使えない。

本書は machine account（`okuri-ai-bot`）と Classic PAT による運用を定義する。

---

## 2. 正本・設定ファイル

| 項目 | 正本 |
| ---- | ---- |
| アカウント定義 | `.github/ai-bot-account.json` |
| 認証検証 CLI | `.github/scripts/gh-bot-auth.cjs` |
| PAT 設定例 | `.github/gh-bot.env.example` |
| Cursor Rule | `.cursor/rules/github-operation.mdc` §3.16 |
| Human Review 経路 | [PRレビュー完了時Status更新ワークフロー仕様書](../../06_実装設計/github_actions/PRレビュー完了時Status更新ワークフロー仕様書.md) §5.2 |

---

## 3. アカウント役割

| アカウント | 種別 | 役割 |
| ---------- | ---- | ---- |
| `okuri-ai-bot` | Machine account | commit / push / Issue 作成 / PR open / AI Review dispatch |
| `ryo-chan-k6` | Personal account | Human Review（Approve / Request changes）、merge、リポジトリ管理 |

Organization 移行は MVP Cycle 3 では行わない。bot は **Collaborator（Write）** として個人リポジトリに参加する。

---

## 4. PAT

| 項目 | 内容 |
| ---- | ---- |
| 発行主体 | **machine account**（`okuri-ai-bot`）。人間アカウントの PAT ではない |
| 種別 | **Classic PAT**（`repo` scope）。Collaborator の private repo では Fine-grained PAT で対象 repo を選べない |
| 保管 | `~/.config/gift-recommend/gh-bot.env`（`chmod 600`）。リポジトリに commit しない |
| 環境変数 | `GH_BOT_TOKEN` |

---

## 5. AI Agent 作業前の必須手順

GitHub へ **書き込む** 操作（commit / push / `gh issue create` / `gh pr create` / **既存 PR への追加 push** / `gh pr edit` / `publish-ai-review-and-dispatch.cjs` / `publish-fix-complete-and-dispatch.cjs`）の前:

```bash
node .github/scripts/gh-bot-auth.cjs verify
eval "$(node .github/scripts/gh-bot-auth.cjs print-setup)"
```

`verify` が `OK: authenticated as okuri-ai-bot` を返すこと。

commit author は bot 名義に揃える（`print-git-user` の JSON を `git -c user.name=... -c user.email=...` に利用）。

---

## 6. Human Review

| 操作 | 実施者 | 備考 |
| ---- | ------ | ---- |
| PR Review → Approve | `ryo-chan-k6` | bot 認証を **解除**（`unset GH_TOKEN` または人間用 gh セッション） |
| PR Review → Request changes | `ryo-chan-k6` | コメントのみでは Status 連動しない。正式 PR Review 必須 |
| merge | `ryo-chan-k6` | AI Agent は merge しない |

---

## 7. 禁止事項

- 人間 PAT で AI 作業用 PR を open・更新すること（author が人間になり Human Review の Approve / Request changes 不可）
- `GH_BOT_TOKEN` を Issue / PR / docs / リポジトリに記載すること
- machine account で Human Review（Approve / Request changes）すること
- machine account で merge すること

---

## 8. E2E 検証

検証手順の記録: [ai-logs/experiments/2026-05-30-bot-author-human-review-e2e.md](../../../ai-logs/experiments/2026-05-30-bot-author-human-review-e2e.md)

再実行スクリプト:

```bash
bash .github/scripts/e2e-bot-author-test-pr.sh
```

---

## 9. 関連ドキュメント

- [AIエージェント活用型 開発運用フロー設計書](./AIエージェント活用型_開発運用フロー設計書.md) §22
- [AIレビュー運用設計書](./AIレビュー運用設計書.md)
- [Commands設計書](./Commands設計書.md) §17 / §18
- [Projects運用ルール](../プロジェクト管理/Projects運用ルール.md) §17.6
