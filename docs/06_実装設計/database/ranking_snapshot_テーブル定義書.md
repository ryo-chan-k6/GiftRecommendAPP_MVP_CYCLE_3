# Ranking Snapshot テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                            |
| -------------- | ------------------------------- |
| ドキュメントID | `DB-TBL-MVP-ranking_snapshot`   |
| ドキュメント名 | Ranking Snapshot テーブル定義書 |
| 対象システム   | Gift Recommendation Service MVP |
| MVP対象        | `yes`                           |
| 作成日         | 2026-06-12                      |
| 更新日         | 2026-06-12                      |

---

## 2. 概要

`ranking_snapshot` は、楽天商品ランキングAPI（BATCH-002）由来の **ランキング取得単位のヘッダ** を保持する Item系 Snapshot テーブルである。

差分反映ではなく、取得対象ランキング（`source` + `external_genre_id` + `period` + `last_build_date`）ごとに 1 ヘッダ行を作成または取得し、その配下の順位明細を `item_popularity_signal` が保持する（1:N）。

**Public API では返却しない**（内部観測データ。Web / API 公開対象外）。

---

## 3. 目的

- 楽天ランキング API の観測条件（ジャンル・期間・API 更新日時）をヘッダとして固定し、再現可能な Snapshot 単位を提供する
- `item_popularity_signal` の親ヘッダおよび冪等キー（`ranking_snapshot_id + rank`）の前提を定義する
- `staging_ranking_signal` → BATCH-008 反映経路との責務境界を明確化する
- 後続 DDL Task が migration を作成できる粒度まで設計を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `ranking_snapshot` |
| 論理テーブル名 | Ranking Snapshot |
| 分類 | Item系 |
| 正本区分 | Snapshot |
| 主な更新主体 | batch（BATCH-002 / IF-DB-BATCH-008） |
| 主な参照主体 | batch（反映・再実行）、reco（IF-DB-RECO-006：最新 Snapshot 経由で人気補助参照） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §4.1 No.2・§8–§11・§16 |

---

## 5. 用途・責務

- 楽天ランキング API レスポンスの **観測単位**（どのジャンル・期間・API ビルド日時のランキングか）をヘッダとして保持する
- テーブル一覧 §5 補足どおり、ランキングはマスタではなく **取得回ごとの Snapshot** として管理する（`external_genre` の Upsert 正本モデルとは異なる）
- 同一観測キー（§7）の再処理時は既存 `ranking_snapshot_id` を再利用し、配下明細を `ranking_snapshot_id + rank` で冪等反映する（バッチ設計方針書 §11.5）
- Online 推薦では全履歴を直接参照せず、**最新 Snapshot** から導出した人気補助シグナルを利用する（バッチ設計方針書 §12.3）

### 5.1 対象外

- ランキング順位明細（`item_popularity_signal` の責務。Batch R02 Task へ委譲）
- 商品正本（`item` の責務）
- Staging 中間データ（`staging_ranking_signal` の責務）
- ジャンル階層マスタ（`external_genre` の責務）
- Public API 公開

### 5.2 `staging_ranking_signal` → `ranking_snapshot` / `item_popularity_signal` 経路

論理ER §9.1 は Staging から `item_popularity_signal` への直接 `upserts` を示すが、物理設計（物理ER §4.1 No.2・バッチ設計方針書 §12.3）では **ヘッダ `ranking_snapshot` を介する 2 層構造** を採用する。

| 観点 | 方針 |
| ---- | ---- |
| データフロー（BATCH-005） | `raw_product_metadata` → `staging_ranking_signal`（Staging 変換） |
| データフロー（BATCH-002 / IF-DB-BATCH-008） | `staging_ranking_signal` またはランキング API 直接レスポンス → `ranking_snapshot`（ヘッダ作成または取得）→ `item_popularity_signal`（明細全件反映） |
| ヘッダ集約 | 同一 API レスポンス内の `source` / `external_genre_id` / `period` / `last_build_date` は 1 ヘッダ行に集約 |
| Staging 物理 FK | `staging_ranking_signal` → `ranking_snapshot` は **LOGICAL**（Staging 系は物理 FK なし。物理ER §17 No.3） |
| 明細 FK | `item_popularity_signal.ranking_snapshot_id` → `ranking_snapshot.ranking_snapshot_id` は **物理 FK ON**（物理ER §9） |

### 5.3 楽天ランキング API マッピング（ヘッダ項目）

| 楽天ランキング API | 物理カラム | 備考 |
| ------------------ | ---------- | ---- |
| （リクエスト / メタ）`genreId` | `external_genre_id` | 観測対象ジャンル。`external_genre` への LOGICAL 参照 |
| `period`（リクエストパラメータ） | `period` | ランキング期間（例: `daily`）。API 仕様に従う文字列 |
| `lastBuildDate` | `last_build_date` | ランキング API 側の更新日時。観測キーに含める |
| — | `source` | MVP 固定 `rakuten` |
| — | `fetched_at` | 本サービスが Snapshot を DB 反映した日時（UTC） |
| — | `batch_run_id` / `api_call_log_id` | 追跡用（任意。LOGICAL 参照） |

> **論理ER §8.4 との責務分離**: `genreId` / `period` / `lastBuildDate` は明細 `item_popularity_signal` にも保持されるが、**観測コンテキストの正本はヘッダ** とする。明細側は Batch R02 Task で冗長列の扱いを定義する。

### 5.4 Snapshot モデル（観測キー・履歴）

| 観点 | 方針 |
| ---- | ---- |
| 観測キー（冪等） | `source` + `external_genre_id` + `period` + `last_build_date`（バッチ設計方針書 §11.5・インターフェース一覧 冪等性方針） |
| 同一キー再処理 | 既存 `ranking_snapshot_id` を **取得して再利用**（INSERT しない）。配下 `item_popularity_signal` を `ranking_snapshot_id + rank` で全件反映 |
| 異なる `last_build_date` | **新規ヘッダ行として履歴追記**（時系列観測の保持） |
| `fetched_at` | 観測キーには **含めない**（再取得日時のメタデータ）。Human Review 論点（§17） |
| 削除 | MVP では物理 DELETE 原則禁止。保持期間ポリシーは後続運用 Task |

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `ranking_snapshot_id` | Ranking Snapshot ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | Snapshot ヘッダ ID |
| 2 | `source` | Data Source | `text` | `yes` | — | — | — | `'rakuten'` | 外部商品データ元。`external_genre.source` / `item.source` と同一コード体系 |
| 3 | `external_genre_id` | External Genre ID | `bigint` | `yes` | — | LOGICAL | — | — | 観測対象ジャンル（楽天 `genreId`）。`external_genre.external_genre_id` 参照 |
| 4 | `period` | Ranking Period | `varchar(32)` | `yes` | — | — | — | — | ランキング期間（楽天 API `period`。例: `daily`, `realtime`） |
| 5 | `last_build_date` | Last Build Date | `timestamptz` | `yes` | — | — | — | — | 楽天ランキング API `lastBuildDate`（観測キー構成要素） |
| 6 | `fetched_at` | Fetched At | `timestamptz` | `yes` | — | — | — | — | 本サービスが当該 Snapshot を反映した日時（UTC） |
| 7 | `batch_run_id` | Batch Run ID | `uuid` | `no` | — | LOGICAL | — | `NULL` | 反映元 Batch Run（`batch_run_log`） |
| 8 | `api_call_log_id` | API Call Log ID | `uuid` | `no` | — | LOGICAL | — | `NULL` | 反映元 API 呼び出しログ |
| 9 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | 行作成日時（物理ER §5 timestamp 方針） |

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `ranking_snapshot_id` | uuid サロゲート PK | 業務エンティティの標準（物理ER §5） |
| UNIQUE | `source`, `external_genre_id`, `period`, `last_build_date` | 観測キー / Snapshot 冪等キー | インターフェース一覧の `snapshot_key` に相当する自然キー。バッチ設計方針書 §11.5 |

> **命名**: 物理 Index 名は `uq_ranking_snapshot_observation_key` を想定（§9）。

---

## 8. 外部キー・参照関係

### 8.1 参照先（本テーブルから）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `external_genre_id` | `external_genre.external_genre_id` | `LOGICAL` | Index 推奨 | #494 確定方針に合わせる。Batch / Staging 系は物理 FK なし（物理ER §17 No.3） |
| `batch_run_id` | `batch_run_log.batch_run_id` | `LOGICAL` | — | 追跡用 nullable |
| `api_call_log_id` | `api_call_log.api_call_log_id` | `LOGICAL` | — | 追跡用 nullable |

> 物理ER §8 FK 表に `external_genre` → `ranking_snapshot` 行は未掲載。本テーブル定義書で **LOGICAL 参照** を確定し、DDL Task または物理ER 整合 Task で追記する。

### 8.2 被参照（子テーブル）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `item_popularity_signal` | `ranking_snapshot_id` | contains | `ON` | 1:N。冪等キー: `ranking_snapshot_id + rank`（テーブル一覧 §14 No.2・物理ER §9） |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `ranking_snapshot_pkey` | `ranking_snapshot_id` | btree（PK） | 主キー | 自動生成 |
| `uq_ranking_snapshot_observation_key` | `source`, `external_genre_id`, `period`, `last_build_date` | unique | 観測キー / get-or-create | §7 と同一 |
| `idx_ranking_snapshot_genre_fetched` | `external_genre_id`, `fetched_at` DESC | btree | ジャンル別の最新 Snapshot 抽出 | reco / batch の「最新 snapshot 選択」（§12.3） |
| `idx_ranking_snapshot_batch_run` | `batch_run_id` | btree | Batch Run 追跡 | nullable |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `ranking_snapshot_pkey` | PRIMARY KEY | `ranking_snapshot_id` | 主キー | — |
| `uq_ranking_snapshot_observation_key` | UNIQUE | `source`, `external_genre_id`, `period`, `last_build_date` | 観測キー一意 | §7 |
| `chk_ranking_snapshot_source_mvp` | CHECK | `source` | `source = 'rakuten'` | MVP 固定。`external_genre` と同型 |
| `chk_ranking_snapshot_period_length` | CHECK | `period` | `char_length(period) BETWEEN 1 AND 32` | — |
| `chk_ranking_snapshot_genre_positive` | CHECK | `external_genre_id` | `external_genre_id >= 0` | 楽天 `genreId`。`0` は root 行参照の可能性あり |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `source` | （code 未定義） | `external_genre` / `item.source` 慣行 | MVP: `rakuten` | enum定義書未 YAML 化。CHECK で MVP 固定 |
| `period` | （code 未定義） | 楽天ランキング API | 例: `realtime`, `daily`, `weekly`, `monthly` | API 仕様に従い varchar 保持。enum Task 化は後続可 |
| — | — | — | — | 状態カラムなし |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| INSERT（新規観測） | batch（BATCH-002 / IF-DB-BATCH-008） | 観測キーが未存在 | 全ヘッダ列 | 観測キー UNIQUE | 新規 `ranking_snapshot_id` 発行 |
| SELECT（既存観測） | batch | 観測キー一致 | — | get-or-create | 既存 `ranking_snapshot_id` を返却 |
| UPDATE | batch | MVP では **ヘッダ列の UPDATE 原則禁止** | `fetched_at`, `batch_run_id`, `api_call_log_id` のみ許容 | — | 観測キー列は不変。再観測は新キーで INSERT |
| DELETE | — | MVP 禁止 | — | — | 履歴 Snapshot は保持 |
| SELECT | reco | 最新 Snapshot 解決後に明細 JOIN | — | — | IF-DB-RECO-006 |

### 12.1 get-or-create 疑似コード

```sql
-- 1) ヘッダ get-or-create
INSERT INTO ranking_snapshot (
  source, external_genre_id, period, last_build_date,
  fetched_at, batch_run_id, api_call_log_id
) VALUES (...)
ON CONFLICT (source, external_genre_id, period, last_build_date) DO NOTHING
RETURNING ranking_snapshot_id;

-- 衝突時は SELECT で既存 ID を取得

-- 2) 明細は item_popularity_signal 側（Batch R02）で
--    ranking_snapshot_id + rank を冪等キーとして全件反映
```

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | MVP では **履歴追記**（観測キーごとに保持）。TTL / アーカイブは後続運用 Task |
| 削除方式 | 物理 DELETE 原則禁止 |
| 削除条件 | — |
| 論理削除 | 列なし |
| アーカイブ | MVP 対象外 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `ranking_snapshot` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: Item 群。`external_genre` の **後**、`item_popularity_signal` の **前**（子 FK の親） |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | batch / reco（service role 経由） |
| 書き込み権限 | batch のみ（BATCH-002 / IF-DB-BATCH-008） |
| service role利用 | Batch Snapshot 反映に限定 |
| 個人情報・機微情報 | 含まない |
| ログ出力制限 | 外部 API 認証情報をログに出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / UNIQUE / Index / CHECK が定義どおり | migration |
| 2 | 観測キー冪等 | 同一 `source` + `external_genre_id` + `period` + `last_build_date` で再実行しても 1 ヘッダ行 | integration |
| 3 | 履歴追記 | `last_build_date` が異なる取得で複数ヘッダ行が保持される | integration |
| 4 | 子 FK 前提 | `item_popularity_signal.ranking_snapshot_id` 物理 FK が成立する | migration |
| 5 | external_genre 整合 | 存在する `external_genre_id` を参照できる（LOGICAL） | manual |
| 6 | Batch 連携 | BATCH-002 後に IF-DB-BATCH-008 でヘッダ + 明細が一貫する | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | 観測キーに `fetched_at` を含めるか | インターフェース一覧は `fetched_at` 代替案を示す一方、バッチ設計方針書は `last_build_date` を採用 | Human | DDL Task 前 | MVP は **§7 どおり `last_build_date` を採用**（推奨案）。再取得のみ異なる場合は別ヘッダが必要 |
| 2 | 履歴 Snapshot の保持上限 | ストレージ・クエリコストに影響 | Human | 運用設計 | MVP は無期限追記。TTL は後続 |
| 3 | `external_genre_id` 物理 FK 採否 | #494 は item 側 LOGICAL を確定。ヘッダでも LOGICAL を本稿で採用 | Human | DDL Task 前 | 本稿は **LOGICAL**（Batch 系方針踏襲） |
| 4 | 物理ER §8 への `external_genre` → `ranking_snapshot` 行追記 | FK 表未掲載 | Human / DDL Task | DDL Task | 本定義書を正として DDL 起票 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | Item 系・FK・冪等キー方針 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §8.4・§9 Staging 経路 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §5 No.15・§14 No.1–2 |
| external_genre 定義書 | `docs/06_実装設計/database/external_genre_テーブル定義書.md` | `external_genre_id` 型・LOGICAL 参照 |
| 外部商品データ連携 | `docs/05_アプリケーション設計/アプリ/外部商品データ連携設計書.md` | §4.3 楽天ランキング API |
| バッチ設計方針書 | `docs/05_アプリケーション設計/アプリ/batch/バッチ設計方針書.md` | §8.4–§8.5・§11.5・§12.3 |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-DB-BATCH-008・冪等キー |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | `source` / `period` 将来 YAML 化 |

---

## 19. レビュー観点

- 物理ER §4.1 No.2・§9・§16・テーブル一覧 §5 / §14 と矛盾していない
- 論理ER §8.4 の API 項目マッピングとヘッダ / 明細の責務分離が明確である
- `external_genre` テーブル定義書 §8.2 と `external_genre_id`（`bigint`）・LOGICAL 参照が整合している
- `item_popularity_signal` との 1:N・冪等キー（`ranking_snapshot_id + rank`）が §8.2・§12 に明記されている
- `staging_ranking_signal` → BATCH-008 経路が §5.2 に整理されている
- バッチ設計方針書 §11.5 の観測キーと一致している
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
