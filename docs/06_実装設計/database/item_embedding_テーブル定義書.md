# Item Embedding テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                              |
| -------------- | --------------------------------- |
| ドキュメントID | `DB-TBL-MVP-item_embedding`       |
| ドキュメント名 | Item Embedding テーブル定義書     |
| 対象システム   | Gift Recommendation Service MVP   |
| MVP対象        | `yes`                             |
| 作成日         | 2026-06-14                        |
| 更新日         | 2026-06-14（Human Review #516 反映） |

---

## 2. 概要

`item_embedding` は、Batch（BATCH-015）が商品テキスト文脈から生成した **Retrieval 用 Embedding ベクトル** を保持する Item派生データ系テーブルである。

`item_id` と生成時に解決した `model_version_id`（Embedding モデル version）をキーとして `embedding_vector`（pgvector）を保存する。Online 推薦（reco）は **参照のみ**、更新は batch のみが行う（論理ER §16.1）。

---

## 3. 目的

- 商品ごとの Embedding ベクトルを DB 上の派生正本として保持し、Retrieval（候補商品の類似検索）に利用する
- 冪等キー（`item_id` + `model_version_id` + `embedding_input_hash`）を物理 DDL で確定し、同一入力・同一モデルでの重複 API 呼び出しを防止する
- `model_version_id` への ON FK 方針を明記し、`model_version_テーブル定義書` §8.1 と整合させる
- `item_meaning`（Matching 用スカラー正本）との責務分離・パイプライン順序を整理する
- 後続 DDL Task が migration（pgvector extension・HNSW Index 含む）を作成できる粒度を提供する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `item_embedding` |
| 論理テーブル名 | Item Embedding |
| 分類 | Item派生データ系 |
| 正本区分 | 派生 / 推薦用正本 |
| 主な更新主体 | batch（BATCH-014 hash 算出、BATCH-015 Embedding 生成） |
| 主な参照主体 | reco（Retrieval / Vector Search）、batch（skip 判定・再生成判定） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11・§15・§17 No.6 |

---

## 5. 用途・責務

- **BATCH-014（Embedding 入力 hash 算出）** で `item_text_context` から `embedding_input_hash` を算出し、**BATCH-015（Item Embedding 生成）** が本テーブルへ Upsert する（テーブル一覧 §7 No.31）
- `item_generation_queue` で `generation_type = embedding` の Queue 行を消化する際、対象 `item_id` の Embedding を生成・保存する
- reco の Retrieval Context が **pgvector 類似検索**で候補 `item_id` を抽出する際の正本（コンテキスト境界定義書 §4.5・RT-01〜05）
- Embedding 値は **Public API へ返さない**（内部検索用。バッチ設計方針書 §13.7）
- **version スナップショット**: BATCH-015 実行時に Config Resolver が解決した `model_version_id`（`model_type = embedding`）を行に固定する

### 5.1 行モデル（MVP）

| 観点 | 方針 |
| ---- | ---- |
| 粒度 | **1 商品 × 1 `model_version_id` × 1 `embedding_input_hash` × 1 `embedding_source_type`** あたり 1 行 |
| 履歴 | 冪等キーが変わる再生成（hash / model version 変更等）は **別行 INSERT**。同一冪等キーは Upsert 上書き |
| Online 参照 | Run 開始時に固定した `model_version_id` で、**同一 model 配下の最新 `generated_at` 1 行**のベクトルを読み取る（§12.3・§17.1 No.6 決定済み） |
| 失敗記録 | 行単位の `generation_status` 列は持たない。失敗は `item_generation_queue` / `error_log` / `phase_log` で追跡（`item_semantic` と同型） |

### 5.2 `embedding_input_hash` 保持方針

| 観点 | 方針 |
| ---- | ---- |
| 保存先 | **本テーブル各行**（`embedding_input_hash` 列。永続化正本） |
| 算出主体 | batch（BATCH-014。`item_text_context` の canonicalize 後 hash） |
| 再生成判定 | hash 変更時は `item_generation_queue` に `generation_type = embedding` で登録（`item_generation_queue_テーブル定義書` §5.4・§5.6） |
| 冪等キー | テーブル一覧 §7・物理ER §11 `uq_item_embedding_idempotent` の構成要素 |
| IF 連携 | IF-DB-BATCH-015 の中間永続は `item_embedding_input`。本テーブル行の `embedding_input_hash` は BATCH-015 が載せる |

> `item_generation_queue` 行には `embedding_input_hash` を持たない（Human Review #507 §17.1 No.4）。hash の正本は派生テーブル側（本テーブル）である。

### 5.3 `model_version_id` 紐づけ方針

| 観点 | 方針 |
| ---- | ---- |
| 解決タイミング | **BATCH-015 実行開始時**に Config Resolver が `model_type = embedding` かつ `is_current = true` の `model_version` を解決 |
| 行への固定 | 解決結果の `model_version_id` を **INSERT / UPDATE 時に行へ保存** |
| FK 方針 | **`ON` 物理 FK**（`model_version_テーブル定義書` §8.1・§5.2 用語補足）。`ON DELETE RESTRICT` |
| 用語補足 | batch 設計書の `embedding_model_version_id` は物理列 **`model_version_id`** と同一概念 |
| reco 参照 | Online 推薦時は Run 開始時に固定した `model_version_id` でベクトル検索する（CF-03 再現性） |

### 5.4 `embedding_source_type` 保持方針

enum定義書 §12.1 No.3 を正本とする。

| 観点 | 方針 |
| ---- | ---- |
| 論理 ID | `embedding_source_type`（`user_feature.source_type` 等とは **別論理 ID**） |
| MVP 有効値 | **`item_text_context` のみ**（enabled: true） |
| 将来値 | `item_text_with_semantic` は enum に定義するが MVP 初期は enabled: false |
| 役割 | Embedding 入力テキストの **構築レシピ種別** を識別する。`embedding_source_version`（構築ルール version ID）は **batch 層の運用概念**であり MVP では物理列に持たない（§17.1 No.2 決定済み） |
| YAML 正本化 | MVP では enum定義書への転記まで。`packages/code-definitions` 正本化は後続 enum Task |

### 5.5 `item_meaning` との関係

| 観点 | `item_meaning` | `item_embedding`（本テーブル） |
| ---- | -------------- | ------------------------------ |
| 正本区分 | 派生 / 推薦用正本（Matching 用スカラー） | 派生 / 推薦用正本（Retrieval 用ベクトル） |
| 主用途 | Social / Symbolic 値の保持（BATCH-013 射影） | 類似検索・候補 recall（BATCH-015 生成） |
| 生成 Batch | BATCH-013（Feature 正規化と連携） | BATCH-014 → BATCH-015 |
| reco 利用 | Matching / Ranking 入力 | Retrieval Context（RT-01〜05） |
| 物理 FK | 相互に **物理 FK なし**（同一 `item_id` 配下の兄弟派生テーブル） |

**パイプライン（Item派生データ系・参照整理）**

```text
item_generation_queue
  → BATCH-010 item_semantic
  → BATCH-011〜013 item_feature → item_meaning（`item_meaning_テーブル定義書` / BATCH-013 射影）
  → BATCH-014 embedding_input_hash 算出
  → BATCH-015 Item Embedding 生成 → item_embedding（本テーブル）
```

- Embedding 生成の入力は **`item_text_context`**（商品名・説明・ジャンル・属性等。BATCH-014）。`item_meaning` 行を直接 JOIN する前提ではない
- `item_semantic` の Concept は `embedding_source_type = item_text_with_semantic` 採用時に文脈へ含め得る（MVP 初期は無効）
- BATCH-016（分布メトリクス）は `item_feature` / `item_meaning` / `item_embedding` を横断参照する（本 Task の out_of_scope）

### 5.6 BATCH パイプラインとの関係

```text
item_generation_queue（generation_type = semantic | feature | embedding）
  → …（semantic / feature 区間は item_feature_テーブル定義書 §5.4 参照）
  → BATCH-014: item_text_context 構築 → embedding_input_hash
  → BATCH-015: External AI Embedding API → item_embedding Upsert
```

再実行単位（バッチ依存関係図）: **`item_id` + `model_version_id` + `embedding_input_hash`**（Embedding 生成失敗時）。

skip 条件（バッチ設計方針書 §13.7）: 同一 `item_id` + `model_version_id` + `embedding_input_hash` で成功済み行が存在する場合、BATCH-015 を skip し得る。

> batch 設計書は `embedding_source_version` を Queue 登録トリガーに列挙する（§8.4）。DB 永続化は **`model_version_id` + `embedding_input_hash` + `embedding_source_type`** のみ（§17.1 No.2 決定済み）。MVP の `embedding_source_type` は `item_text_context` 固定のため、skip 判定は物理 unique 3 列で足りる。

### 5.7 対象外

- `item_meaning` テーブル定義書本体の再定義（`item_meaning_テーブル定義書` を正本とする）
- `user_embedding` / `query_embedding`（User意味推定系）
- `embedding_input_hash` 算出アルゴリズム詳細（BATCH-014 バッチ仕様書）
- `embedding_source_type` の packages/code-definitions YAML 正本化（後続 enum Task）
- api からの直接 DML
- Public API への `embedding_vector` 露出（#469 委譲）
- DDL / migration / pgvector extension 適用本体（DDL Task へ委譲）

### 5.8 Online / Batch 責務境界

| 主体 | 許可操作 | 禁止 |
| ---- | -------- | ---- |
| batch（BATCH-015） | INSERT / UPDATE（Upsert） | — |
| batch（BATCH-014） | 本テーブルへの DML なし（hash は BATCH-015 行へ記録） | — |
| reco | SELECT（Vector Search） | INSERT / UPDATE / DELETE |
| api | — | 直接参照なし（MVP） |
| Online 推薦中 | — | **本テーブルを更新しない**（論理ER §16.1） |

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `item_embedding_id` | Item Embedding ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK |
| 2 | `item_id` | Item ID | `uuid` | `yes` | — | `ON` | — | — | 対象商品。`item.item_id` 参照 |
| 3 | `model_version_id` | Model Version ID | `uuid` | `yes` | — | `ON` | — | — | Embedding モデル version。`model_version` 参照（`model_type = embedding`） |
| 4 | `embedding_source_type` | Embedding Source Type | `text` | `yes` | — | — | — | — | 入力構築レシピ種別。enum定義書 §12.1 No.3 |
| 5 | `embedding_input_hash` | Embedding Input Hash | `varchar(64)` | `yes` | — | — | — | — | BATCH-014 算出 hash。冪等キー構成要素 |
| 6 | `embedding_vector` | Embedding Vector | `vector(1536)` | `yes` | — | — | — | — | pgvector 型。MVP 現行モデル `text-embedding-3-small`（§17.1 No.3 決定済み） |
| 7 | `generated_at` | Generated At | `timestamptz` | `yes` | — | — | — | — | Embedding 生成完了日時（UTC）。BATCH-015 完了時に設定 |

> **論理ER §10.2**: 物理列名は **`embedding_input_hash`**（Human Review #516 §17.1 No.1 決定済み。論理ER §10.2 も同名に更新済み）。
>
> batch 設計書 §13.7 の `embedding_source_version` / `generation_status` は **DB 列に持たない**。`embedding_source_type` でレシピ種別を保持し、構築ルール version 変更は Queue トリガー + batch ログで追跡する（§17.1 No.2 決定済み）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `item_embedding_id` | サロゲート UUID | — |
| UNIQUE | `item_id`, `model_version_id`, `embedding_input_hash` | 再生成冪等キー | Index 名: `uq_item_embedding_idempotent`（物理ER §11・テーブル一覧 §7） |

同一商品・同一モデル version で入力 hash が変わった場合は **別行** として INSERT する（履歴保持）。同一冪等キーでの再実行は Upsert 上書きとする（§12.2）。

---

## 8. 外部キー・参照関係

### 8.1 参照先（本テーブルから）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `item_id` | `item.item_id` | `ON` | `ON DELETE RESTRICT` | `item_テーブル定義書` §8.2 と同型 |
| `model_version_id` | `model_version.model_version_id` | `ON` | `ON DELETE RESTRICT` | `model_version_テーブル定義書` §8.1 generates_with |

### 8.2 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| reco（Retrieval） | `embedding_vector` 等 | reads | アプリ層 | pgvector 類似検索。Online 参照のみ |
| BATCH-016（分布メトリクス） | 集計参照 | reads | アプリ層 | 本 Task の out_of_scope |
| `item_generation_queue` | `item_id` 経由 | output_of | アプリ層 | BATCH-015 消化先（Queue 定義書 §8.3） |

### 8.3 `item_meaning` との関係（論理・パイプライン）

| 観点 | 方針 |
| ---- | ---- |
| 関係種別 | 同一 `item_id` 配下の **兄弟派生テーブル**（has 関係は `item` 経由） |
| 直接 FK | **なし**（`item_meaning_テーブル定義書` と兄弟派生。Matching 用スカラー vs Retrieval 用ベクトル） |
| 生成順序 | Feature 正規化（BATCH-013）で `item_meaning` 射影と、Embedding（BATCH-014〜015）は **並行し得る** が、`generation_type = embedding` の Queue 消化は Feature 済み前提（Queue 定義書 §5.6） |
| reco 責務 | `item_meaning` → Matching / `item_embedding` → Retrieval（コンテキスト境界定義書） |

### 8.4 論理ER / 物理ER / batch 設計 差分整理

| 論点 | 論理ER §10.2 | 物理ER §11 / テーブル一覧 §7 | batch 設計書 §13.7 | 本定義書の採用（MVP・HR #516 決定済み） |
| ---- | ------------ | ----------------------------- | ------------------- | ------------------------------------- |
| 入力 hash 列名 | `embedding_input_hash` | `embedding_input_hash` | `embedding_input_hash` | **`embedding_input_hash`** |
| モデル version 列名 | `model_version_id` | `model_version_id` | `embedding_model_version_id` | **`model_version_id`** |
| 入力レシピ識別 | `embedding_source_type` | （§12 enum 連携） | `embedding_source_version` も運用列挙 | **`embedding_source_type` 列のみ**。source version は Queue トリガー |
| 冪等キー | 3 列相当 | 3 列 unique | 4 要素（+ source_version） | **物理ER 3 列 unique** + skip は §12.5 |
| 生成状態 | なし | なし | `generation_status` | **列なし**（Queue / error_log） |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `item_embedding_pkey` | `item_embedding_id` | btree（PK） | 主キー | 自動生成 |
| `uq_item_embedding_idempotent` | `item_id`, `model_version_id`, `embedding_input_hash` | unique btree | 再生成冪等 | 物理ER §11 |
| `idx_item_embedding_item_model` | `item_id`, `model_version_id` | btree | Online 参照 | 物理ER §10。現行モデルでの行取得 |
| `idx_item_embedding_vector` | `embedding_vector` | **hnsw** | 類似検索 | 物理ER §10・§17 No.6。MVP 第一候補 |
| `idx_item_embedding_item_id` | `item_id` | btree | FK 補助・障害調査 | batch 再実行単位の抽出 |

### 9.1 HNSW Index 方針（MVP）

| 観点 | 方針 |
| ---- | ---- |
| 方式 | **HNSW**（物理ER §17 No.6 決定済み。migration 正本と同型） |
| 距離関数 | **cosine**（`vector_cosine_ops`）。migration 正本と一致 |
| パラメータ | **`m = 16` / `ef_construction = 64`** を MVP 正式値とする（migration 正本と同値） |
| 性能根拠 | TV-006 PoC（類似検索単体・テストデータ）。1,000 件 HNSW p95 ≈ 2〜3 ms。10,000 件 HNSW p95 ≈ 5.6〜6.6 ms。暫定 **Go**。詳細は [TV-006 結果](../../90_PoC/技術検証結果/TV-006_pgvector検索性能検証結果.md) / [1万件超](../../90_PoC/技術検証結果/TV-006_後続_1万件超_pgvector検索性能検証結果.md)（後者は #1574 取込後に develop 着） |
| DDL 変更 | **不要**（現行 migration を維持。本反映でパラメータを覆さない） |
| 後追い | 商品数が極少の初期は vector Index を後追い作成してもよい（物理ER §17 No.6 備考） |
| 未計測 | JOIN + Hard Filter 込みの本番 Retrieval 経路、および本番カタログ分布は未計測。件数スケール判断は pgvector 単体の範囲に限定する |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `item_embedding_pkey` | PRIMARY KEY | `item_embedding_id` | 主キー | — |
| `uq_item_embedding_idempotent` | UNIQUE | §7 の 3 列 | 冪等キー一意 | テーブル一覧 §7 |
| `fk_item_embedding_item_id` | FOREIGN KEY | `item_id` | `item(item_id)` ON DELETE RESTRICT | §8.1 |
| `fk_item_embedding_model_version_id` | FOREIGN KEY | `model_version_id` | `model_version(model_version_id)` ON DELETE RESTRICT | §8.1 |
| `chk_item_embedding_source_type` | CHECK | `embedding_source_type` | MVP は `item_text_context` のみ許容 | enum定義書 §12.1 No.3 |
| `chk_item_embedding_input_hash_format` | CHECK | `embedding_input_hash` | `char_length(embedding_input_hash) = 64` かつ hex 形式 | SHA-256 想定（BATCH-014 仕様 Task） |
| `chk_item_embedding_vector_dims` | CHECK | `embedding_vector` | `vector_dims(embedding_vector) = 1536` | MVP 現行モデル `text-embedding-3-small`（§17.1 No.3 決定済み） |

> MVP では単一 Embedding モデル（1536 次元）を前提とする。将来 `model_version` 追加で次元が異なる場合は DDL Task で列設計を再検討する。

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `embedding_source_type` | `embedding_source_type` | enum定義書 §12.1 No.3 | MVP: `item_text_context` のみ | 将来: `item_text_with_semantic`（enabled: false） |

### 11.1 MVP `embedding_source_type`

| value | MVP | 説明 |
| ----- | --- | ---- |
| `item_text_context` | **有効** | 商品名・説明・ジャンル・属性等から構築したテキスト文脈 |
| `item_text_with_semantic` | 定義のみ（無効） | Semantic Concept を文脈に含めるレシピ。後続で有効化 |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| INSERT / UPSERT | batch（BATCH-015） | 対象 item の Embedding 生成成功 | `embedding_vector`, `embedding_input_hash`, `embedding_source_type`, `generated_at` 等 | `uq_item_embedding_idempotent` | External AI API 呼び出し後 |
| SELECT | reco | Run 時 `model_version_id` 固定 | — | — | pgvector 類似検索。Online 更新禁止 |
| SELECT | batch | skip 判定・再生成判定 | — | — | hash / version 比較 |
| DELETE | batch（メンテナンス） | §13 保持方針に基づく | 古い世代行 | 定期実行 | 現行世代は保持 |
| INSERT / UPDATE / DELETE | api / reco | — | — | **禁止** | 論理ER §16.1 |

### 12.1 `model_version_id` 解決フロー

```text
1. BATCH-015 が model_type = embedding の current model_version を Config Resolver で解決
2. 解決した model_version_id を行へ記録
3. 同一 model_version_id + embedding_input_hash で冪等 Upsert
```

### 12.2 BATCH-015 Upsert 疑似コード

```sql
INSERT INTO item_embedding (
  item_id,
  model_version_id,
  embedding_source_type,
  embedding_input_hash,
  embedding_vector,
  generated_at
) VALUES (
  :item_id,
  :model_version_id,
  :embedding_source_type,
  :embedding_input_hash,
  :embedding_vector,
  now()
)
ON CONFLICT (
  item_id,
  model_version_id,
  embedding_input_hash
) DO UPDATE SET
  embedding_vector = EXCLUDED.embedding_vector,
  embedding_source_type = EXCLUDED.embedding_source_type,
  generated_at = EXCLUDED.generated_at;
```

### 12.3 Online 参照フロー（reco / Retrieval）

§17.1 No.6 決定済み。

```text
1. Run 開始時に model_version_id（embedding）を固定
2. 候補 item_id ごとに、同一 model_version_id 配下で generated_at が最大の行を 1 件特定
3. 当該行の embedding_vector で pgvector 類似検索
4. Retrieval は recall 重視（RT-01）。final_score 算出は Matching / Ranking の責務（RT-05）
5. active な item のみ対象（item.active_status 等は Retrieval 前フィルタ。詳細は reco 実装 Task）
```

**現行世代解決（疑似 SQL）:**

```sql
SELECT DISTINCT ON (item_id)
       item_embedding.*
  FROM item_embedding
 WHERE item_id = ANY(:item_ids)
   AND model_version_id = :model_version_id
 ORDER BY item_id, generated_at DESC;
```

### 12.4 `item_generation_queue` 連携

| `generation_type` | 消化 Batch | 本テーブルへの影響 |
| ----------------- | ---------- | ------------------ |
| `semantic` | BATCH-010 → … → BATCH-015 | 一連完了後に行が存在し得る |
| `feature` | BATCH-011〜013（必要時 BATCH-014〜015） | 同上 |
| `embedding` | BATCH-014 → BATCH-015 | **本テーブルが直接出力先** |

再生成トリガー（Queue 定義書 §5.6）: `embedding_model_version_id` / `embedding_source_version` / `embedding_input_hash` 変更 → `generation_type = embedding`（`embedding_source_version` は batch 層トリガー。DB 列なし）。

### 12.5 skip 判定（batch）

バッチ設計方針書 §13.7: 同一 `item_id` + `model_version_id` + `embedding_input_hash` で **成功済み** `item_embedding` 行が存在する場合、BATCH-015 を skip し `item_generation_queue` を `skipped` へ遷移し得る。

> batch 設計書の 4 要素運用（`embedding_source_version` 含む）と DB unique 3 列の差は §8.4。MVP は `embedding_source_type = item_text_context` 固定のため、入力文脈の同一性は `embedding_input_hash` に内包される前提で 3 列 skip とする。構築ルール version 変更は Queue 登録で再生成を起動する。

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（Retrieval 再現性・監査）。**現行世代**（Run / batch が参照する model + hash 組）は削除しない |
| 削除方式 | 原則 **物理 DELETE はメンテナンスのみ**。Online / 通常 batch では DELETE しない |
| 削除条件 | **非現行** 冪等キー行のみ。MVP は運用メンテナンス時の **最小 DELETE** に限定（§17.1 No.5 決定済み・`item_feature_テーブル定義書` §13 と同型） |
| 論理削除 | 採用しない |
| アーカイブ | MVP では対象外 |
| キャッシュ | Redis 等の item_embedding cache は別層（基盤構成設計書）。DB 正本は本テーブル |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `item_embedding` |
| migration単位 | Item派生データ系 migration（`item` / `model_version` 等の先行テーブル後） |
| 適用順序 | 物理ER §15: **pgvector extension** → Master / Config → `item` → `item_semantic` → `item_feature` → `item_meaning`（先行）→ **`item_embedding`** |
| rollback方針 | DDL Task で定義。派生データのため DROP は開発環境のみ想定 |
| 破壊的変更有無 | `no`（新規テーブル） |

**pgvector 前提**

```sql
-- DDL Task で先行適用（物理ER §15）
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | `apps/reco`（service role）、`apps/batch`（service role） |
| 書き込み権限 | `apps/batch` のみ（BATCH-015） |
| service role利用 | Supabase service role 経由。client 直アクセス禁止 |
| 個人情報・機微情報 | 商品 Embedding のみ。個人データを含まない |
| ログ出力制限 | `embedding_input_hash` / `embedding_vector` をログに全文出力しない |
| Public API | `embedding_vector` は **非公開**（内部 Retrieval 専用） |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | pgvector extension・テーブル・FK・unique・HNSW Index が migration で作成される | migration |
| 2 | 冪等キー | 同一 3 列で Upsert が上書き、hash 変更で別行 INSERT される | integration |
| 3 | FK | `item_id` / `model_version_id` の RESTRICT が機能する | integration |
| 4 | embedding_source_type CHECK | MVP 許容値以外が拒否される | migration |
| 5 | pgvector 検索 | HNSW Index を用いた類似検索が実行できる（次元 1536） | integration |
| 6 | BATCH-014/015 連携 | hash 算出後に同一冪等キー行へ vector が保存される | integration |
| 7 | Online 境界 | api / reco からの INSERT / UPDATE / DELETE が行われない | manual |
| 8 | 権限 | batch のみが書き込み可能 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review #516 にて No.1〜6 を決定済み（§17.1） |

### 17.1 Human Review 決定事項（Issue #516）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | `source_text_hash` vs `embedding_input_hash` | 物理列名は **`embedding_input_hash`**。論理ER §10.2 も同名に更新 | Human | §6・§8.4・enum定義書 §12.1 |
| 2 | `embedding_source_version` 列の物理化 | **MVP は物理列なし**。`embedding_source_type` + `embedding_input_hash` + `model_version_id` で永続化。source version 変更は Queue トリガー（batch 層） | Human | §5.4・§8.4・`item_generation_queue_テーブル定義書` §5.6 |
| 3 | `embedding_vector` 次元数 | **`vector(1536)`**。MVP 現行モデル `text-embedding-3-small` | Human | §6・§10 `chk_item_embedding_vector_dims` |
| 4 | HNSW パラメータ（`m` / `ef_construction`） | **MVP 正式値: `m = 16` / `ef_construction = 64`**（migration 正本と同値）。TV-006 PoC で現状維持 **Go**（#1590 で正式 docs 反映） | Human（#516）→ 性能検証後に具体値確定（#1590） | §9.1 |
| 5 | 非現行世代行の DELETE ポリシー | **`item_feature` と同型**。現行世代保持・メンテナンス時のみ非現行行 DELETE | Human | §13 |
| 6 | Online 参照時の「現行世代」解決 | 同一 **`model_version_id` で最新 `generated_at` 1 行** | Human | §12.3 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| TV-006 PoC（〜1,000） | `docs/90_PoC/技術検証結果/TV-006_pgvector検索性能検証結果.md` | HNSW 件数スケール根拠 |
| TV-006 PoC（1万件超） | `docs/90_PoC/技術検証結果/TV-006_後続_1万件超_pgvector検索性能検証結果.md` | 1万件超根拠（#1574） |
| TV-006 設計反映メモ | `docs/90_PoC/技術検証結果/設計反映メモ_TV-006.md` | 正式反映ステータス |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | FK・Index・制約・pgvector 方針 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2 属性・§16 責務境界 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §7 No.31・冪等キー |
| コンテキスト境界定義書 | `docs/04_ドメインモデル設計/コンテキスト境界定義書.md` | Retrieval Context |
| 利用技術スタック整理表 | `docs/05_アプリケーション設計/基盤/利用技術スタック整理表.md` | pgvector 採用 |
| item 定義書 | `docs/06_実装設計/database/item_テーブル定義書.md` | item_id FK |
| model_version 定義書 | `docs/06_実装設計/database/model_version_テーブル定義書.md` | §8.1 ON FK |
| item_generation_queue 定義書 | `docs/06_実装設計/database/item_generation_queue_テーブル定義書.md` | 再生成トリガー |
| item_semantic 定義書 | `docs/06_実装設計/database/item_semantic_テーブル定義書.md` | 入力文脈参照 |
| item_feature 定義書 | `docs/06_実装設計/database/item_feature_テーブル定義書.md` | パイプライン参照 |
| item_meaning 定義書 | `docs/06_実装設計/database/item_meaning_テーブル定義書.md` | Matching 用スカラー正本・パイプライン |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | §12.1 embedding_source_type |
| バッチ設計方針書 | `docs/05_アプリケーション設計/アプリ/batch/バッチ設計方針書.md` | §13.6〜13.7 BATCH-014/015 |
| バッチ処理一覧 | `docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md` | 入出力 |
| バッチ依存関係図 | `docs/05_アプリケーション設計/アプリ/batch/バッチ依存関係図.md` | 再実行単位 |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-DB-BATCH-015 |
| 処理構成定義書 | `docs/05_アプリケーション設計/アプリ/処理構成定義書.md` | MOD-BATCH-035/036 |

---

## 19. レビュー観点

- テーブル一覧 §7 No.31・論理ER §10.2・物理ER §8–§11 と矛盾していない
- 冪等キー 3 列・`embedding_input_hash` / `model_version_id` / `embedding_source_type` 方針が明記されている
- `model_version_id` への物理 FK ON が `model_version_テーブル定義書` §8.1 と一致している
- `item_meaning` との関係（Matching vs Retrieval・パイプライン順序）が明記されている
- pgvector / HNSW Index 方針（`m` / `ef_construction` 含む）が migration 正本と一致し、TV-006 根拠を辿れる
- BATCH-014 / BATCH-015・`item_generation_queue` との整合が取れている
- 論理ER §16.1 / §16.2（Batch 更新・Online 参照のみ）が反映されている
- §17.1 決定事項（No.1〜6）が本文（§6 / §8.4 / §9.1 / §10 / §12.3 / §13）に反映されている
- secret や `.env` 実値が含まれていない
