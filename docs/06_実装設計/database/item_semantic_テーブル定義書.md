# Item Semantic テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                              |
| -------------- | --------------------------------- |
| ドキュメントID | `DB-TBL-MVP-item_semantic`        |
| ドキュメント名 | Item Semantic テーブル定義書      |
| 対象システム   | Gift Recommendation Service MVP   |
| MVP対象        | `yes`                             |
| 作成日         | 2026-06-14                        |
| 更新日         | 2026-06-14                        |

---

## 2. 概要

`item_semantic` は、Batch（BATCH-010）が商品情報から抽出した **Semantic Concept 派生データ** を保持する Item 派生データ系テーブルである。

`item_id` と生成時に解決した `semantic_config_version_id` をキーとして `semantic_json`（Concept 抽出結果）を保存する。Online 推薦（reco）は **参照のみ**、更新は batch のみが行う（論理ER §16.2）。

---

## 3. 目的

- 商品名・説明・ジャンル・属性等から抽出した Semantic Concept を DB 上の派生正本として保持する
- `semantic_config_version_id` を行に固定し、Rule / Concept 定義 version 変更後も **再現性** を担保する
- BATCH-010 出力・BATCH-011 以降（Feature 入力 hash / Feature 生成）の入力正本として後続 Batch / reco が参照できる粒度を提供する
- 後続 DDL Task が migration を作成できる粒度まで物理定義を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `item_semantic` |
| 論理テーブル名 | Item Semantic |
| 分類 | Item派生データ系 |
| 正本区分 | 派生 |
| 主な更新主体 | batch（BATCH-010） |
| 主な参照主体 | batch（BATCH-011〜012）、reco（Post Hard Filter / Matching 等） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§12 |

---

## 5. 用途・責務

- **BATCH-010（Item Semantic 生成）** の出力先（テーブル一覧 §7 No.28・バッチ処理一覧 BATCH-010）
- `item_generation_queue` で `generation_type = semantic` の Queue 行を消化する際、対象 `item_id` の Semantic Concept を生成・Upsert する
- `semantic_rule` / `semantic_concept`（同一 `semantic_config_version_id` 配下）に基づき Concept を抽出し、結果を `semantic_json` に格納する
- reco は Online 推薦中に **SELECT のみ**（論理ER §16.2）。Matching / Hard Filter の入力として利用する
- **version スナップショット**: 生成時に Config Resolver が解決した `semantic_config_version_id` を行に保持し、後から `is_current` が切り替わっても当該行の意味は不変（`semantic_config_version_テーブル定義書` §12 と同型）

### 5.1 対象外

- Item Feature / Item Meaning / Item Embedding の生成結果（別 Task / 別テーブル）
- `feature_input_hash` / `embedding_input_hash` の永続化（BATCH-011 / BATCH-014 出力。別整理）
- `item_generation_queue` 本体（Queue 制御は `item_generation_queue_テーブル定義書`）
- api からの直接 DML
- DDL / migration 本体（DDL Task へ委譲）
- OpenAPI / generated 変更（Epic 終盤 Task #469 へ委譲）

### 5.2 Online / Batch 責務境界

| 主体 | 許可操作 | 禁止 |
| ---- | -------- | ---- |
| batch（BATCH-010） | INSERT / UPDATE（Upsert） | — |
| batch（BATCH-011〜） | SELECT | 本テーブルへの DML（hash / Feature は別出力） |
| reco | SELECT | INSERT / UPDATE / DELETE |
| api | — | 直接参照なし（MVP） |
| Online 推薦中 | — | **本テーブルを更新しない** |

> 論理ER §16.1 の「Online 推薦中に更新しない」一覧には `item_feature` / `item_embedding` は含まれるが **`item_semantic` は未列挙**。MVP では `item_feature` と同様 **Online 中は batch 更新・reco 参照のみ** とする（§17.1 No.6 参照）。

### 5.3 `semantic_json` 保持方針

Semanticルール定義書 §4・§13・バッチ設計方針書 §13.2 を正本とする。`semantic_config_version_id` は **列で保持**し、JSON 内には重複保存しない。

| キー | 必須 | 型 | 説明 |
| ---- | ---- | -- | ---- |
| `concepts` | ○ | array | 抽出 Concept の配列（0 件以上） |
| `concepts[].concept_code` | ○ | string | `semantic_concept.concept_code` と同一命名（snake_case） |
| `concepts[].confidence` | ○ | number | 0.0〜1.0。Semanticルール定義書 §9 |
| `concepts[].input_intent` | △ | string | Item 側は原則 `neutral`（Semanticルール定義書 §7.1） |
| `concepts[].assertion_polarity` | △ | string | MVP は `asserted` 固定可 |
| `concepts[].extraction_method` | ○ | string | `keyword` / `phrase` / `pattern` / `llm` / `hybrid` |
| `concepts[].source_type` | ○ | string | `item_name` / `item_caption` / `item_description` / `item_genre` / `item_tag` 等 |
| `concepts[].evidence_texts` | △ | string[] | 根拠テキスト（複数可・§14.3） |

**JSON 例**

```json
{
  "concepts": [
    {
      "concept_code": "formal_refined",
      "confidence": 0.85,
      "input_intent": "neutral",
      "assertion_polarity": "asserted",
      "extraction_method": "phrase",
      "source_type": "item_description",
      "evidence_texts": ["上質な包装", "贈答用"]
    },
    {
      "concept_code": "safe_classic",
      "confidence": 0.72,
      "input_intent": "neutral",
      "assertion_polarity": "asserted",
      "extraction_method": "keyword",
      "source_type": "item_name",
      "evidence_texts": ["定番"]
    }
  ]
}
```

| 観点 | 方針 |
| ---- | ---- |
| Concept 参照 | JSON 内は **`concept_code` 参照**（`semantic_concept_id` への物理 FK は張らない） |
| version 内 valid 性 | BATCH-010 実行時、当該 `semantic_config_version_id` かつ `is_active = true` の Concept のみ出力（`semantic_concept_テーブル定義書` §5） |
| 重複 Concept | 同一 `concept_code` は **confidence 最大値で統合**（Semanticルール定義書 §14.2） |
| 採用閾値 | MVP は `confidence >= 0.60` を通常採用ライン（Semanticルール定義書 §9.4） |
| Public API | 本テーブル / `semantic_json` は **Public 非公開**（内部派生データ） |

### 5.4 `semantic_config_version_id` 紐づけ方針

| 観点 | 方針 |
| ---- | ---- |
| 解決タイミング | **BATCH-010 実行開始時**に Config Resolver が `is_current = true`（親 `semantic_config.is_active = true` 前提）を解決 |
| 行への固定 | 解決結果の `semantic_config_version_id` を **INSERT / UPDATE 時に行へ保存**（実行後の `is_current` 切替の影響を受けない） |
| Queue との関係 | `item_generation_queue` 行には version 列を持たない（#507 §17.1 No.4）。trace は `batch_run_log` / `phase_log` / 本テーブル行で行う |
| reco 参照 | Online 推薦時は **item に紐づく最新生成行**を `item_id` + 必要な `semantic_config_version_id`（Run 固定 version または current 解決）で SELECT。詳細は reco 実装 Task |
| item_feature 連携 | `item_feature` も同一 `semantic_config_version_id` を保持（`semantic_config_version_テーブル定義書` §8.2）。Feature 再生成時の version 整合は後続 Task で確定 |

### 5.5 BATCH-010 入出力

| 方向 | 内容 |
| ---- | ---- |
| 入力 | `item_generation_queue`（`generation_type = semantic`）、`item`（名称・説明等）、`external_genre`（LOGICAL）、属性 / タグ、`semantic_config_version_id`（Resolver 解決）、`semantic_rule` / `semantic_concept` |
| 出力 | 本テーブルへの Upsert、`item_generation_queue.queue_status` 更新（Queue 定義書 §12.2） |
| モジュール | `MOD-RECO-026` Item Semantic Generator（処理構成定義書・機能×モジュール対応表） |
| skip | 同一 `item_id` + `semantic_config_version_id` で入力不変かつ既存行あり → Queue `skipped` 可（バッチ設計方針書 §14.1） |

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `item_semantic_id` | Item Semantic ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | 派生行 ID |
| 2 | `item_id` | Item ID | `uuid` | `yes` | — | `ON` | — | — | 対象商品。`item.item_id` 参照 |
| 3 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `ON` | — | — | 生成時に利用した意味定義 version |
| 4 | `semantic_json` | Semantic JSON | `jsonb` | `yes` | — | — | — | — | Concept 抽出結果（§5.3） |
| 5 | `generated_at` | Generated At | `timestamptz` | `yes` | — | — | — | — | 生成完了日時（UTC） |

> 論理ER §10.2 の属性（`item_semantic_id` / `item_id` / `semantic_config_version_id` / `semantic_json` / `generated_at`）と一致。入力 hash 列は論理ER 上なし（Feature 側は `item_feature` が `feature_input_hash` を保持）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `item_semantic_id` | サロゲート UUID | — |
| UNIQUE | `item_id`, `semantic_config_version_id` | **1 商品 × 1 意味定義 version あたり 1 行** | Upsert 冪等キー（§17.1 No.2 決定済み） |

**履歴方針**: 異なる `semantic_config_version_id` への再生成は **別行として保持**（version 横断の履歴）。同一 version 内の再生成は UNIQUE により Upsert 上書き。

---

## 8. 外部キー・参照関係

### 8.1 参照先（本テーブルから）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `item_id` | `item.item_id` | `ON` | `ON DELETE RESTRICT` | `item_テーブル定義書` §8.2 と同型 |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | `ON DELETE RESTRICT` | §17.1 No.1 決定済み。`item_feature` と同型 |

### 8.2 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `item_feature`（後続 Task） | `item_id` + `semantic_config_version_id` | input | `LOGICAL` / 部分 `ON` | Feature 生成入力。`item_feature` Task で確定 |
| BATCH-011 | `item_id` 経由 SELECT | reads | アプリ層 | Feature 入力 hash 算出 |
| reco | `item_id` 経由 SELECT | reads | アプリ層 | Post Hard Filter 等 |
| `semantic_concept` | `semantic_json` 内 `concept_code` | generates_with | `LOGICAL` | `concept_code` + 行の `semantic_config_version_id` で特定 |
| `semantic_rule` | 間接（BATCH-010 実行） | applied_by | アプリ層 | Rule 正本は `semantic_rule` テーブル |

### 8.3 `item_generation_queue` との生成経路

```text
BATCH-009: item_generation_queue INSERT（generation_type=semantic）
    ↓
BATCH-010: queue_status=processing
    ↓ Config Resolver → semantic_config_version_id
    ↓ Item Semantic Generator（item + rules）
    ↓ Upsert item_semantic（item_id + semantic_config_version_id）
    ↓
BATCH-011〜: item_semantic SELECT → feature_input_hash / item_feature
```

Queue 行との物理 FK は **張らない**（`item_id` 経由の論理関連のみ。`item_generation_queue_テーブル定義書` §8.3）。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `item_semantic_pkey` | `item_semantic_id` | btree（PK） | 主キー | 自動生成 |
| `uq_item_semantic_item_version` | `item_id`, `semantic_config_version_id` | btree（unique） | Upsert 冪等・1:1（version 単位） | §7 |
| `idx_item_semantic_item_id` | `item_id` | btree | item 単位 JOIN・BATCH-011 入力 | reco / batch |
| `idx_item_semantic_version_id` | `semantic_config_version_id` | btree | version 単位参照・監査 | — |
| `idx_item_semantic_generated_at` | `generated_at` DESC | btree | 最新生成調査・メンテナンス | 任意だが MVP 推奨 |

> 物理ER §10 には `item_semantic` 専用 Index 行が未記載。本 Task で上記を確定し、Epic 横断で物理ER §10 追記を別 Task 化する（§17 未決なし・§19 レビュー観点参照）。

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `item_semantic_pkey` | PRIMARY KEY | `item_semantic_id` | 主キー | — |
| `uq_item_semantic_item_version` | UNIQUE | `item_id`, `semantic_config_version_id` | 冪等 Upsert キー | §7 |
| `fk_item_semantic_item_id` | FOREIGN KEY | `item_id` | `item(item_id)` ON DELETE RESTRICT | §8.1 |
| `fk_item_semantic_semantic_config_version_id` | FOREIGN KEY | `semantic_config_version_id` | `semantic_config_version(semantic_config_version_id)` ON DELETE RESTRICT | §8.1 |
| `chk_semantic_json_object` | CHECK | `semantic_json` | `jsonb_typeof(semantic_json) = 'object'` | — |
| `chk_semantic_json_concepts_array` | CHECK | `semantic_json` | `jsonb_typeof(semantic_json -> 'concepts') = 'array'` | §5.3 |

> `concept_code` 個別値の CHECK は MVP では **アプリ層 + seed 整合**に委ねる（`semantic_concept` と同型。固定 18 code CHECK なし）。

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| — | — | なし | — | 状態カラムなし |

`semantic_json` 内の `extraction_method` / `source_type` / `input_intent` は Semanticルール定義書・enum Task 横断の code 値を使用する（DB CHECK は MVP 最小限）。

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| UPSERT | batch（BATCH-010） | §12.1 生成条件 | `semantic_json`, `generated_at` | `item_id` + `semantic_config_version_id` | §12.2 |
| SELECT | batch（BATCH-011〜） | `item_id` 指定 | — | — | Feature 入力 |
| SELECT | reco | `item_id`（+ version 条件） | — | — | Matching / Filter |
| INSERT / UPDATE / DELETE | api / reco | — | — | **禁止** | Online 中更新禁止 |
| DELETE | batch（メンテナンス） | §13 保持方針 | 孤児行・保持期間経過 | 定期 | §13.1 |

### 12.1 BATCH-010 生成条件

```text
1. item_generation_queue から generation_type=semantic, queue_status=queued を取得
2. queue_status = processing へ遷移（Queue 定義書 §5.7）
3. Config Resolver: semantic_config.is_active=true → is_current=true の semantic_config_version_id を解決
4. item + semantic_rule + semantic_concept を入力に Concept 抽出
5. semantic_json を組み立て（§5.3）
6. item_semantic を Upsert（§12.2）
7. 成功時 Queue succeeded / skip 時 skipped（Queue 定義書 §12.2）
```

**skip 判定（代表）**

| 条件 | 動作 |
| ---- | ---- |
| 同一 `item_id` + `semantic_config_version_id` の行が存在し、入力商品テキスト・Rule version に対する再抽出結果が実質同一 | Queue `skipped`（item_semantic 行は更新しない、または `generated_at` のみ更新は **しない**） |
| 意味影響項目変更・Rule 変更・version 変更 | Upsert 実行 |

### 12.2 Upsert 疑似 SQL

```sql
INSERT INTO item_semantic (
  item_id,
  semantic_config_version_id,
  semantic_json,
  generated_at
) VALUES (
  :item_id,
  :semantic_config_version_id,
  :semantic_json::jsonb,
  now()
)
ON CONFLICT (item_id, semantic_config_version_id)
DO UPDATE SET
  semantic_json = EXCLUDED.semantic_json,
  generated_at = EXCLUDED.generated_at;
```

| 観点 | 方針 |
| ---- | ---- |
| 衝突キー | `uq_item_semantic_item_version`（§7） |
| 上書き対象 | `semantic_json`, `generated_at` のみ（`item_semantic_id` は不変） |
| 新 version | 新 `semantic_config_version_id` → **新規 INSERT**（履歴保持） |

### 12.3 再生成トリガー（代表）

テーブル一覧 §7 補足・`item_generation_queue_テーブル定義書` §5.4 と整合。

| トリガー | 期待動作 |
| -------- | -------- |
| 意味影響 Item 属性変更 → Queue `semantic` | 同一 current version で Upsert |
| `semantic_config_version_id`（current）変更のみ | 新 version 行を INSERT（旧 version 行は保持） |
| BATCH-010 失敗 → Queue `failed` → 再 `queued` | 同一 version で再 Upsert |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | **長期**（Item 有効期間中。物理ER §13 Item 正本・派生） |
| 削除方式 | 原則 **物理 DELETE しない** |
| 削除条件 | 親 `item` 削除は RESTRICT。孤児化防止 |
| 論理削除 | 列なし |
| アーカイブ | MVP 対象外 |

### 13.1 例外 DELETE（メンテナンス）

| 対象 | 方針 |
| ---- | ---- |
| 親 `item` が `active_status = excluded` かつ長期非参照 | 運用判断で version 履歴を含め DELETE 可（Human Review 必須・MVP では未自動化） |
| 誤生成・テストデータ | 運用 DELETE（監査ログ必須） |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `item_semantic` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: **`item`・`semantic_config_version` 作成後**。`item_generation_queue` と **並行可**。`item_feature` より **先**（BATCH-010 → BATCH-012 依存） |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | batch / reco（service role 経由） |
| 書き込み権限 | batch（BATCH-010）のみ |
| service role利用 | Batch Upsert・reco SELECT に限定 |
| 個人情報・機微情報 | 商品説明由来テキストを `semantic_json` に含み得る。Public API 非公開 |
| ログ出力制限 | `semantic_json` 全文を Public ログに出力しない。必要時は concept_code 一覧程度に mask |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK / UNIQUE が定義どおり | migration |
| 2 | FK 整合 | 存在しない `item_id` / `semantic_config_version_id` への INSERT が拒否される | migration |
| 3 | UNIQUE Upsert | 同一 `item_id` + `semantic_config_version_id` の 2 行目 INSERT が Upsert になる | integration |
| 4 | version 履歴 | 異なる `semantic_config_version_id` で 2 行保持できる | integration |
| 5 | JSON CHECK | `concepts` 欠落 JSON が拒否される | migration |
| 6 | BATCH-010 連携 | Queue 消化後に行が存在し `generated_at` が更新される | integration |
| 7 | reco 参照 | Online 推薦パスが SELECT のみであること（DML なし） | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review #513 にて No.1〜6 を決定（下記 §17.1） |

### 17.1 Human Review 決定事項（Issue #513）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | `semantic_config_version_id` FK | **物理 FK ON**（`ON DELETE RESTRICT`） | Human（提案） | `item_feature`・`semantic_config_version_テーブル定義書` §8.2 と整合。`user_semantic` は LOGICAL だが Item 派生は ON を採用 |
| 2 | Upsert / Unique キー | **`item_id` + `semantic_config_version_id` UNIQUE**。同一 version 内 Upsert、version 変更時は **別行 INSERT** | Human（提案） | テーブル一覧 §7 再生成判定・Feature 入力 hash 整合 |
| 3 | version 解決タイミング | **BATCH-010 実行時**に current version を解決し、**行へ固定保存** | Human（提案） | Queue 行に version 列なし（#507 No.4）との整合 |
| 4 | `semantic_json` スキーマ | **`concepts[]` 配列**。要素は `concept_code` / `confidence` / `extraction_method` / `source_type` 必須、`evidence_texts` 推奨 | Human（提案） | Semanticルール定義書 §4・§13 準拠 |
| 5 | 旧行扱い（同一 version 再生成） | **Upsert 上書き**（`semantic_json` + `generated_at`）。履歴テーブルは MVP 作らない | Human（提案） | 監査は `batch_run_log` / `phase_log` |
| 6 | Online 更新禁止 | **`item_feature` と同様 reco 参照のみ**。論理ER §16.1 一覧への `item_semantic` 追記は **別 docs Task** | Human（提案） | 本定義書 §5.2 で MVP 境界を明示 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | Item派生データ系・§13 保持 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2 属性・§16 責務境界 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §7 No.28 |
| 正本定義表 | `docs/05_アプリケーション設計/アプリ/database/正本定義表.md` | 派生データ正本 |
| SemanticConcept定義書 | `docs/04_ドメインモデル設計/SemanticConcept定義書.md` | Concept 体系 |
| Semanticルール定義書 | `docs/04_ドメインモデル設計/Semanticルール定義書.md` | 抽出・confidence |
| バッチ設計方針書 | `docs/05_アプリケーション設計/アプリ/batch/バッチ設計方針書.md` | §13.2 / §13.3 |
| バッチ処理一覧 | `docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md` | BATCH-010 |
| バッチ依存関係図 | `docs/05_アプリケーション設計/アプリ/batch/バッチ依存関係図.md` | BATCH-009→010→011 |
| 処理構成定義書 | `docs/05_アプリケーション設計/アプリ/処理構成定義書.md` | MOD-RECO-026 |
| item 定義書 | `docs/06_実装設計/database/item_テーブル定義書.md` | §8.2 item_id FK |
| semantic_config_version 定義書 | `docs/06_実装設計/database/semantic_config_version_テーブル定義書.md` | §8.2 被参照 |
| semantic_concept 定義書 | `docs/06_実装設計/database/semantic_concept_テーブル定義書.md` | §8.2 concept_code |
| semantic_rule 定義書 | `docs/06_実装設計/database/semantic_rule_テーブル定義書.md` | BATCH-010 Rule 正本 |
| item_generation_queue 定義書 | `docs/06_実装設計/database/item_generation_queue_テーブル定義書.md` | §8.3 生成経路 |

---

## 19. レビュー観点

- 論理ER §10.2・テーブル一覧 §7 No.28 と矛盾していない
- `semantic_config_version_id` の FK（ON）・解決タイミング・Upsert キーが §5.4 / §7 / §12 で明示されている
- `item_テーブル定義書` §8.2（item_id ON）・`item_generation_queue_テーブル定義書` §8.3（BATCH-010 経路）と整合している
- `semantic_json` が Semanticルール定義書・`semantic_concept` の concept_code 参照方針と一致している
- 論理ER §16.2（batch 更新）・§5.2（Online 参照のみ）が反映されている
- apps/** / OpenAPI / generated / DDL 変更が含まれていない
- secret や `.env` 実値が含まれていない
