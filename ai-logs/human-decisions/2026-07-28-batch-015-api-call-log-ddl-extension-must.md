# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-07-28-batch-015-api-call-log-ddl-extension-must` |
| Log種別 | `human-decision` |
| 件名 | BATCH-015 Embedding の `api_call_log` DB 本配線を **DDL 拡張込みの別 Task（Must）** とする |
| 発生日時 | 2026-07-28 |
| 記録日時 | 2026-07-28 |
| 関連Issue | #1705（判断発生元） / **#1710**（Wave 5） / Epic #1636 |
| 関連PR | #1706 |
| Definition | `prompts/definitions/tasks/batch-observability-e4/batch-apply-001-017.yaml` |
| 重要度 | `high` |
| 状態 | `decided` |

---

## 2. 結論

PR #1706 / Issue #1705 の Human Review 観点「015 の `api_call_log` DB 未配線を継続してよいか」について、**案 B を採用**する。

| 項目 | 決定 |
| ---- | ---- |
| Wave 4（#1705） | 015 は Run/Phase/Error のみ。`api_call_log` DB は **この PR では未配線のまま**（DDL 制約のため） |
| 後続 | **DDL 拡張 + BATCH-015 `api_call_log` DB 本配線を別 Task で必須化（E4 Wave 5 = #1710）** |
| 方針 | 時間より確実性を優先。Embedding 呼出監査を楽天と同型で DB 完結させる |

あわせて同一 Human Review の次は推奨方針で確定済み。

| 確認事項 | 決定 |
| -------- | ---- |
| 1. §8.1 案 C（001〜017、018/019 除外） | **OK** |
| 3. 017 の `job_run_id` / `batch_run_id` 分離 | **OK** |
| 4. 未マップ中間 phase の DB スキップ継続 | **OK** |

---

## 3. 理由（要約）

- 未配線のままでは Embedding（IF-EXT-005）呼出の成否・latency・rate_limit を DB で横断調査できない
- BATCH-015 仕様は `api_call_log` INSERT を想定しており、メモリのみでは監査要件未達
- 現行 DDL（`source='rakuten'` CHECK / `source_api` 楽天系 4 値）では正本どおりの INSERT が不可
- 時間をかけてでも、障害解析を楽天と同型に揃える方が運用上確実

---

## 4. 選択肢（判断時）

| 案 | 内容 | 採否 |
| -- | ---- | ---- |
| A | E4 では未配線継続。DDL 拡張は任意の後続 | 不採用（暫定放置になりやすい） |
| **B** | **DDL 拡張 + 015 api_call DB を別 Task で早めに必須化** | **採用** |
| C | `api_call_log` を楽天専用と明文化し Embedding は別経路 | 不採用（BATCH-015 / §8.2 のねらいと乖離） |

---

## 5. 後続 Task（Wave 5）で実施すること

| 区分 | 内容 |
| ---- | ---- |
| DDL / enum | `chk_api_call_log_source_mvp` 拡張、`source_api` に Embedding 用値追加、定義書・enum YAML・migration |
| 実装 | BATCH-015 `record_api_call` → `PostgresApiCallLogWriter` 本配線（secret / ベクトル全文禁止は維持） |
| docs | ギャップ一覧・api_call_log 定義書・Observability・BATCH-015 の整合 |
| 検証 | UT + local Postgres 疎通（secret 非出力） |

### 5.1 Wave 5 内で再確認する詳細（本ログでは未確定）

| 項目 | 推奨案（推論） | 備考 |
| ---- | -------------- | ---- |
| `source` 追加値 | `openai` | `item.source`（マーケット）とは別概念である点を定義書で明示 |
| `source_api` 追加値 | `item_embedding` または `embedding` | enum定義書 §6.24 / `source_api.yaml` 更新が必要 |
| Epic 完了条件 | Wave 5 完了を E4 Epic 完了の前提に含める | Epic #1636 / Projects で明示 |

---

## 6. 反映対象

| 対象 | 内容 |
| ---- | ---- |
| ギャップ一覧 | §1.2 / §6 / §8.4 / §11 / §12 に Human 確定・Wave 5 を追記 |
| 本ログ | 判断正本（Issue 化前〜後続 Task 起票までの記録） |
| 後続 | Wave 5 Task Definition / Issue **#1710** / Branch（#1705 merge 後・no-branch 解除） |
| #1705 / #1706 | Wave 4 としては 015 api_call 未配線を残ギャップとして継続。Human Review 観点 2 は本決定でクローズ |

---

## 7. 確認した事実

- `api_call_log` は `source = 'rakuten'` CHECK（`chk_api_call_log_source_mvp`）
- `source_api` 許容値は `item_search` / `item_ranking` / `genre_search` / `attribute_search` のみ
- BATCH-015 は in-memory `api_call_logs` のみ。Run/Phase/Error は Wave 4 で DB 配線
- 017 の `fetched_count` / `embedding_generated_count` は 015 の api_call DB に直接依存しない

---

## 8. 関連情報

| 種別 | 参照 |
| ---- | ---- |
| docs | `docs/05_アプリケーション設計/アプリ/batch/バッチ観測横断・本実装ギャップ一覧.md` |
| docs | `docs/06_実装設計/database/api_call_log_テーブル定義書.md` |
| docs | `docs/06_実装設計/batch/BATCH-015_Item Embedding生成バッチ仕様書.md` |
| Issue | #1705 / #1636 |
| PR | #1706 |
