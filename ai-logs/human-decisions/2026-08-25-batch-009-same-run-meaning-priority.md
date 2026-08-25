# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-08-25-batch-009-same-run-meaning-priority` |
| Log種別 | `human-decision` |
| 件名 | BATCH-009: 同一 daily run 取得商品の meaning 優先方針 |
| 発生日時 | 2026-08-25 |
| 記録日時 | 2026-08-25 |
| 発生元 | #1818 品質確認 → 調査 Issue #1878 |
| 関連Issue | #1878（本調査） / #1818 / #1811 / #1745 |
| 重要度 | `medium` |
| 状態 | **`pending`（Human 判断待ち）** |

---

## 2. 調査結論（事実）

2026-08-25 06:33 daily SUCCEEDED で、同一 run 取得商品 `flowerkitchen:10000437` が meaning 未処理だった主因は次のとおり。

| 仮説 | 採否 | 根拠 |
| ---- | ---- | ---- |
| H1: meaning chain が `--diff-batch-run-id` 未渡し | **採択（主因）** | `lor_run_meaning_chain` は `--max-items` / `--source` のみ。007 側は `--diff-batch-run-id` あり |
| H2: §9.2 非意味影響のみで除外 | **却下（本件）** | 強制 evaluate すると `should_register=True` / `generation_type=semantic`（hash 変更） |
| H3: `product_diff_result_id` 並び + 読取窓 | **採択（メカニズム）** | `max_items=100` → 先頭 500 行窓。当該 UUID は窓外（`4cc8d065...` > 先頭窓末尾） |
| H4: §18.1 No.5 選定既定が提案のまま | **採択（ギャップ）** | 「対象 batch_run_id」提案未確定。GHA meaning 複合子も `diff_batch_run_id` 未配線 |

再現（読取のみ）:

- フィルタなし plan: 100 件選定、当該商品 **不在**、選定 `batch_run_id` は 49 種の歴史バックログ
- `diff_batch_run_id=<import pipeline>`: **1 件**で当該商品のみ選定

---

## 3. Human 判断依頼

| No | 論点 | 選択肢 |
| --: | ---- | ---- |
| 1 | 同一 run 優先を MVP 要件にするか | **A.** する（import の `pipeline_batch_run_id` を 009 に渡す） / **B.** しない（バックログ消化優先を維持） / **C.** 両立（同一 run 優先 + 残枠でバックログ） |
| 2 | BATCH-009 §18.1 No.5 選定既定 | **A.** 対象 `batch_run_id` を **確定** / **B.** 提案のまま（任意指定のみ） |
| 3 | local orchestrator / GHA 配線 | No.1 採択に応じて後続 fix Task 化 |

### 3.1 推奨案（AI）

**選択肢 C（同一 run 優先 + 残枠バックログ）** を推奨。

| 理由 | 内容 |
| ---- | ---- |
| 運用期待 | daily で取れた商品が同日 meaning に乗らないと推薦品質が遅延する |
| 仕様整合 | §18.1 No.5 提案（対象 batch_run_id）と整合しやすい |
| リスク低減 | バックログ消化を完全放棄しない |

実装イメージ（後続 Task・本 Log では未実施）:

1. `lor_run_meaning_chain` で import の `scenario_pipeline_id` を `--diff-batch-run-id` として 009 に渡す
2. 同一 run 分を処理後、残 `max_items` でフィルタなしバックログを処理するかは別途設計
3. GHA `batch-item-meaning-generation` も同様に親 import Run ID を渡せるよう整理

---

## 4. 境界

- 本 Log は調査結果と判断依頼のみ。実装・crontab 変更は行わない
- secret / `.env` 実値は記録しない
- #1818 最低限確認（親シェル完走）の成否とは分離して扱う

---

## 5. 後続アクション

| 対象 | 内容 | 状態 |
| ---- | ---- | ---- |
| Human | No.1〜3 を判断 | **待ち** |
| #1878 | 調査結果コメント・完了条件チェック | 本更新 |
| 後続 | 採択方針に応じた fix/docs Task 起票 | Human 判断後 |

---

## 6. 参照

- Issue #1878
- `docs/06_実装設計/batch/BATCH-009_商品意味生成キュー登録バッチ仕様書.md` §9.2 / §18.1 No.5
- `scripts/batch/lib/local_orchestrator_common.sh`（`lor_run_meaning_chain`）
- `apps/batch/src/batch/application/item_generation_queue/repositories.py`
- `.github/workflows/batch-item-meaning-generation.yml`
