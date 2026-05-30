# Fix Review Comments Result

正本テンプレート。`/fix-review-comments` 完了時に PR へ投稿し、`publish-fix-complete-and-dispatch.cjs` が Fix Outcome を読み取って Status 同期を dispatch する。

## 1. 対応結果

| 項目 | 内容 |
| ---- | ---- |
| Fix Outcome | `ready_for_ai_review` |
| 対象PR | `#<PR番号>` |
| 対象Issue | `#<Issue番号>` |
| 対象Branch | `<branch名>` |

### 対応した指摘

- （箇条書き）

### 修正内容

- （箇条書き）

### 変更ファイル

- （箇条書き）

### 再実行したテスト・検証

- （箇条書き）

### 未対応の指摘

- なし

### 未対応理由

- なし

### Human確認事項

- なし

## 12. Status更新意図

| 項目 | 内容 |
| ---- | ---- |
| 現在Status | `In Progress` |
| 次Status | `AI Review` |

### 次に実行するCommand

```text
/review-pr @<review-definition> #<PR番号>
```

---

## Fix Outcome 値

| Fix Outcome | Status dispatch | 意味 |
| ----------- | --------------- | ---- |
| `ready_for_ai_review` | **実行する** | 指摘対応完了・再 AI Review 可能 |
| `needs_human_decision` | 実行しない | Human 判断待ち |
| `split_required` | 実行しない | 別 Issue 化が必要 |
| `partial_fix` | 実行しない | 一部対応・再レビュー不可 |
| `blocked` | 実行しない | 前提不足で対応不可 |

`ready_for_ai_review` 以外の場合も PR コメントは投稿してよいが、`publish-fix-complete-and-dispatch.cjs` は dispatch をスキップする。
