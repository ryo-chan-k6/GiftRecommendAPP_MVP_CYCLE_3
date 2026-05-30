# Human Review 指摘対応パターン E2E 検証

## 目的

1 本の bot author PR で A-1 → A-2 → B → C を順に検証する。

| 項目 | 値 |
|------|-----|
| Task Issue | （Phase 0 後に記入） |
| PR | （Phase 0 後に記入） |
| Branch | `docs/task-<issue>-review-fix-patterns-e2e` |
| Task Definition | `prompts/definitions/_e2e/review-fix-patterns-e2e/task.yaml` |
| Review Definition | `prompts/definitions/_e2e/review-fix-patterns-e2e/pr-review.yaml` |

## Phase 0 チェックリスト

- [ ] Task Issue 作成
- [ ] Branch 作成（workflow）
- [ ] bot PR open（author = `okuri-ai-bot`）
- [ ] Projects Status = `AI Review`
- [ ] AI Review → `Human Review`

## 結果サマリ（Phase 1〜4）

| Phase | パターン | Pass | 備考 |
|-------|---------|------|------|
| 1 | A-1 | | |
| 2 | A-2 | | |
| 3 | B | | |
| 4 | C | | |
