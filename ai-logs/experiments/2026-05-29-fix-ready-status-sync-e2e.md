# fix 完了時 Status 同期 E2E

## 目的

`/fix-review-comments` 完了時の `publish-fix-complete-and-dispatch.cjs` と `pr-ready-for-ai-review.yml` の live 検証。

## 手順

1. `feat/fix-complete-status-dispatch` を develop へ PR / merge（または feature branch で workflow_dispatch）
2. bot PAT で検証用 PR を open（author = `okuri-ai-bot`）
3. 対象 Task Issue の Projects Status を `In Progress` にする
4. `publish-fix-complete-and-dispatch.cjs` を実行
5. Actions `fix-ready · dispatch · PR #n` 成功、Status = `AI Review` を確認

## 記録

| 項目 | 値 |
|------|-----|
| 検証 PR | （記入） |
| Task Issue | （記入） |
| dispatch run | （記入） |
| Status 遷移 | （記入） |

## 後片付け

検証 PR は Close 可（merge 不要）。
