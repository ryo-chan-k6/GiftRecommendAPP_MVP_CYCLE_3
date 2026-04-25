## 1. 目的

本書は、ログ設計方針書に基づき、ログテーブルの具体的な定義を行うことを目的とする。

- ログテーブル構造
- カラム定義
- ログ種別・役割
- トレーサビリティ設計
- 運用・保持方針

---

## 2. ログ設計の全体構造

本システムではログを以下の責務で分離する。

| 種類         | テーブル                       | 役割               |
| ------------ | ------------------------------ | ------------------ |
| 実行トレース | `recommendation_run_event_log` | 成否・障害追跡     |
| 行動ログ     | `user_interaction_log`         | ユーザー行動       |
| 観測ログ     | `metric_log`                   | 分析・評価・改善用 |
| 評価記録     | `recommendation_feedback`      | 明示評価（正本）   |
| 人手評価     | `human_eval_result`            | 評価記録（正本）   |

---

## 3. 設計の基本方針

### 3-1. ログの責務分離

| ログ種別    | 責務           |
| ----------- | -------------- |
| event_log   | 成否・トレース |
| metric_log  | 分析・観測     |
| feedback    | 業務評価       |
| eval_result | 評価結果       |

---

### 3-2. event_typeの設計

**原則**

- ログ対象の「種別」を表す
- 状態は含めない

```
event_type = recommendation_run / phase
```

---

### 3-3. statusの設計

**原則**

- 成否のみを表す
- 状態遷移は扱わない

```
status = success / failed
```

---

### 3-4. ログと状態の分離

| 要素           | 管理場所           |
| -------------- | ------------------ |
| 状態遷移       | recommendation_run |
| 成否ログ       | event_log          |
| 実行時間・数値 | metric_log         |

---

# 4. 推薦実行ログ

---

## 4-1. テーブル定義

### `recommendation_run_event_log`

| カラム                | 型          | 必須 | 説明                           |
| --------------------- | ----------- | ---- | ------------------------------ |
| event_log_id          | uuid        | ○    | PK                             |
| recommendation_run_id | uuid        | ○    | 実行単位                       |
| event_type            | varchar     | ○    | `recommendation_run` / `phase` |
| phase_name            | varchar     | △    | phaseの場合のみ                |
| status                | varchar     | ○    | `success` / `failed`           |
| error_code            | varchar     | △    | エラーコード                   |
| message               | text        | △    | 詳細                           |
| payload_json          | jsonb       | △    | 補助情報                       |
| occurred_at           | timestamptz | ○    | 発生時刻                       |

---

## 4-2. 設計意図

### 役割

- トランザクション成否管理
- 障害トレース
- 再実行判断

---

### event_type

| 値                 | 意味               |
| ------------------ | ------------------ |
| recommendation_run | レコメンド実行単位 |
| phase              | 内部処理単位       |

---

### status

| 値      | 意味 |
| ------- | ---- |
| success | 成功 |
| failed  | 失敗 |

---

### 例

| event_type         | phase_name | status  |
| ------------------ | ---------- | ------- |
| recommendation_run | -          | success |
| phase              | ranking    | success |
| phase              | retrieval  | failed  |

---

## 4-3. インデックス

- `(recommendation_run_id, occurred_at)`
- `(event_type)`
- `(status)`
- `(phase_name)`

---

## 4-4. 設計ポイント

- 状態遷移は持たない
- 成否のみ記録
- phase粒度でトレース可能
- 分析用途は持たない

---

# 5. ユーザー行動ログ

---

## 5-1. テーブル定義

### `user_interaction_log`

| カラム                        | 型          | 必須 | 説明         |
| ----------------------------- | ----------- | ---- | ------------ |
| interaction_log_id            | uuid        | ○    | PK           |
| recommendation_result_item_id | uuid        | ○    | 商品単位     |
| recommendation_run_id         | uuid        | △    | 実行単位     |
| event_type                    | varchar     | ○    | イベント種別 |
| user_id                       | uuid        | △    | ユーザー     |
| session_id                    | varchar     | △    | セッション   |
| payload_json                  | jsonb       | △    | 補助         |
| occurred_at                   | timestamptz | ○    | 発生時刻     |

---

## 5-2. event_type

| 値           | 意味     |
| ------------ | -------- |
| item_viewed  | 表示     |
| item_clicked | クリック |

---

## 5-3. インデックス

- `(recommendation_result_item_id, occurred_at)`
- `(user_id, occurred_at)`
- `(event_type)`

---

## 5-4. 設計ポイント

- 高頻度ログ
- 行動分析の基礎
- view/click統合

---

# 6. メトリクスログ

---

## 6-1. テーブル定義

### `metric_log`

| カラム                | 型          | 必須 | 説明     |
| --------------------- | ----------- | ---- | -------- |
| metric_log_id         | uuid        | ○    | PK       |
| recommendation_run_id | uuid        | ○    | 実行単位 |
| item_id               | uuid        | △    | 商品     |
| phase_name            | varchar     | △    | フェーズ |
| metric_name           | varchar     | ○    | 指標名   |
| metric_value          | float       | ○    | 値       |
| occurred_at           | timestamptz | ○    | 時刻     |

---

## 6-2. metric例

| metric_name       | 内容         |
| ----------------- | ------------ |
| run_duration_ms   | 実行時間     |
| phase_duration_ms | フェーズ時間 |
| candidate_count   | 候補数       |
| result_count      | 結果数       |
| score_mean        | 平均スコア   |

---

## 6-3. インデックス

- `(recommendation_run_id)`
- `(metric_name)`
- `(phase_name)`
- `(occurred_at)`

---

## 6-4. 設計ポイント

- 分析専用
- 数値中心
- event_logと責務分離

---

# 7. 評価ログ（参考）

---

## 7-1. recommendation_feedback

| カラム                        | 説明         |
| ----------------------------- | ------------ |
| recommendation_result_item_id | 対象         |
| feedback_type                 | like/dislike |
| score                         | 評価         |
| comment                       | コメント     |

---

## 7-2. human_eval_result

| カラム             | 説明     |
| ------------------ | -------- |
| human_eval_task_id | 作業単位 |
| eval_score         | スコア   |
| eval_comment       | コメント |

---

# 8. トレーサビリティ設計

---

## 8-1. キー構造

| キー                          | 用途     |
| ----------------------------- | -------- |
| recommendation_run_id         | 実行単位 |
| recommendation_result_item_id | 商品単位 |
| human_eval_task_id            | 評価単位 |

---

## 8-2. トレース構造

```
recommendation_run
   ├── recommendation_run_event_log
   ├── metric_log
   └── recommendation_result_item
           ├── user_interaction_log
           ├── recommendation_feedback
           └── human_eval_task
                   └── human_eval_result
```

---

# 9. JSON設計方針

---

## 使用する場合

- 可変項目
- デバッグ情報

---

## 使用しない場合

- JOINキー
- 頻繁に検索する項目

---

# 10. 保存期間

| 種類       | 期間  |
| ---------- | ----- |
| 実行ログ   | 180日 |
| 行動ログ   | 180日 |
| メトリクス | 30日  |
| 評価       | 1年   |
| エラー     | 1年   |

---

# 11. 運用設計

---

## 11-1. 削除

- TTLで削除
- 古いデータは集約

---

## 11-2. 分析

- metric_log → 分布
- interaction_log → 行動分析

---

## 11-3. 障害対応

- event_log 起点で調査

---

# 12. 物理設計への引継ぎ

次工程で実施

- DDL作成
- INDEX設計
- パーティション
- TTL

---

# 一言まとめ

**事実**

- event_logは「成否」
- metric_logは「観測値」

**推論**

- この分離により
  👉 シンプルで拡張性の高いログ設計になる
