# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-06-02-fixer-auto-dispatch-ai-review-request-changes` |
| Log種別 | `human-decision` |
| 件名 | AI Review の `request_changes` も Fixer 自動 dispatch 対象に含める |
| 発生日時 | 2026-06-02 |
| 記録日時 | 2026-06-02 |
| 発生元Command | Epic #308 着手時の Human 判断 |
| 発生元Agent | （Human 直接） |
| workstream_key | `fixer-auto-dispatch` |
| 関連Issue | `#308` |
| 関連PR | （未作成） |
| Definition | `prompts/definitions/epics/fixer-auto-dispatch/epic.yaml` |
| 重要度 | `medium` |
| 状態 | `resolved` |

---

## 2. 結論

**AI Review の `request_changes` も Fixer 自動 dispatch の対象とする。** Human Review の `changes_requested` のみを対象とする案は採用しない。

---

## 3. human-decision として記録する理由

Fixer 自動化の契機範囲は運用フロー全体に影響し、AI Review と Human Review で非対称のままにすると Request changes 後の手動起動が残るため。

### 3.1 記録対象理由

- Epic #308 の設計・workflow 統合・skip 条件の前提となる
- `pr-review-status-sync.yml` の両 route（`repository_dispatch` / `pull_request_review`）に実装影響する

### 3.2 通常作業ログではない理由

通常作業ログをすべて `ai-logs/` に保存しない。本ログは Fixer dispatch 契機の範囲という人間判断を記録する。

---

## 4. 確認できた事実

| 区分 | 内容 |
| ---- | ---- |
| 事実 | Human Review の `changes_requested` は `pr-review-status-sync.yml` の `pull_request_review` で Status `In Progress` に更新されるが、Fixer は未 dispatch |
| 事実 | AI Review の `request_changes` は `publish-ai-review-and-dispatch.cjs` 経由の `ai_review_status_sync`（repository_dispatch）で同 workflow に入る |
| 事実 | 修正完了 → 再 AI Review は `fix-ready` で自動化済み（#303 系） |
| 事実 | 実例 PR #306 で Human Request changes 後 Fixer 未自動起動 |

---

## 5. 選択肢と判断

| 選択肢 | 内容 | 判断 |
| ------ | ---- | ---- |
| A | Human Review の `changes_requested` のみ Fixer 自動 dispatch | 不採用 |
| B | AI Review の `request_changes` と Human Review の `changes_requested` の双方を対象 | **採用** |

**採用理由（Human）:** `/review-pr` 自動化と対称にし、AI Review 指摘後も人手で `/fix-review-comments` を起動しない運用にする。

**リスク（推論）:** AI Review の `request_changes` が scope 外・Human 判断必須を含む場合、誤って Fixer が起動する可能性がある → skip 条件で設計 Task が明示的に扱う。

---

## 6. 実装への反映先

| 正本 | 反映内容 |
| ---- | -------- |
| `prompts/definitions/epics/fixer-auto-dispatch/epic.yaml` | `scope` / `objective` / `human_decision_points` / `notes` |
| GitHub Issue #308 | §15.2 Human Review 観点 → 確定事項 |
| 子 Task（設計） | dispatch 契機・skip 条件の正本 |

---

## 7. 未確定事項（別 Human 判断）

（なし — 2026-06-02 時点で Epic #308 着手前判断は確定済み）

---

## 7.1 Fixer dispatch 失敗時の recovery（確定: 2026-06-02）

| 項目 | 内容 |
| ---- | ---- |
| 判断 | dispatch 失敗時は **手動 CLI** で recovery。workflow 自動リトライ / 別 `workflow_dispatch` は採用しない |
| 前提 | dispatch 失敗 → `process.exitCode=1` → job failure → Fixer Definition Run Harness は未 dispatch |
| nuance | 同一 job 内の先行 step（Status `In Progress` 等）は完了済みの可能性あり |
| 実装 | `dispatch-fix-review-harness.cjs` が `recovery_command` を JSON 出力（`dispatch-review-pr-harness.cjs` と同型） |

---

## 8. 判断者

| 項目 | 内容 |
| ---- | ---- |
| 判断者 | `ryo-chan-k6` |
| 判断日 | 2026-06-02 |
