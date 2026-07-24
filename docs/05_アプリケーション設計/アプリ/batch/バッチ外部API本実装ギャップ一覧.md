# バッチ外部API本実装ギャップ一覧

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | E3 棚卸し正本（docs） |
| 対象 | 楽天 / Embedding / Object Storage / Semantic（LLM）× BATCH-001〜017 |
| 作成日 | 2026-07-24 |
| 更新日 | 2026-07-24（初版） |
| 関連 Epic | [#1598](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1598) |
| 関連 Task | [#1599](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1599)（T1） |
| 先行 | E0 横串ギャップ / E1 親 workflow / E2 IF-DB・DDL（#1595 MERGED） |

### 1.1 目的

外部 API stub × Batch CLI × env の現状を突合し、E3 後続（実 client・CLI 配線・UT）の Human 判断材料を正本化する。

### 1.2 本ドキュメントでやらないこと

| out of scope | 理由 |
| ------------ | ---- |
| HTTP / OpenAI 実クライアント実装 | 後続 Task |
| CLI 本接続配線の実装 | 後続 Task |
| production / CI での無承認 live 呼出 | Human 承認必須 |
| BATCH-018 Reco IF 本接続 | E0 §10 どおり E3 除外 |
| 親 / 複合 workflow 改修 | E1 完了・本 Epic 外 |
| IF-DB / DDL | E2 完了・本 Epic 外 |

### 1.3 区分

| 区分 | 意味 |
| ---- | ---- |
| 事実 | リポジトリ上の実装・docs から確認できる内容 |
| 推論 | 事実から導いた影響・推奨 |
| Human 確認 | 方針確定が必要な事項 |

---

## 2. 30秒サマリ（事実）

| 項目 | 状態 |
| ---- | ---- |
| Rakuten client | `ScaffoldRakutenApiClient` のみ。HTTP 実装なし |
| Embedding client | `ScaffoldEmbeddingClient`（決定論的疑似ベクトル）。実 OpenAI 呼出なし |
| Object Storage | `ScaffoldObjectStorageClient` のみ |
| Semantic 生成 | `ScaffoldItemSemanticAdapter`（Rule-first / LLM 非呼出） |
| CLI 非 `--scaffold-demo` | 設定検証後、多くは「Real … not enabled」で **exit 3** |
| E2 との関係 | DbWriter / 代表 UPSERT は利用可能。外部 I/O は未接続 |

---

## 3. 外部境界の現状（事実）

| 境界 | Protocol / 入口 | Scaffold 実装 | 実 client | factory 切替 |
| ---- | --------------- | ------------- | --------- | ------------ |
| 楽天 API | `RakutenApiClient` | `ScaffoldRakutenApiClient` | **なし** | **なし** |
| Embedding（IF-EXT-005） | `EmbeddingClient` | `ScaffoldEmbeddingClient` | **なし** | **なし** |
| External AI（汎用） | `ExternalAiClient` | `ScaffoldExternalAiClient` | **なし** | **なし** |
| Object Storage | `ObjectStorageClient` | `ScaffoldObjectStorageClient` | **なし** | **なし** |
| Item Semantic 生成 | adapter（batch 内） | `ScaffoldItemSemanticAdapter` | **なし**（LLM） | **なし** |
| Item Embedding 生成 | adapter（batch 内） | `ScaffoldItemEmbeddingAdapter` | ScaffoldEmbedding 経由 | **なし** |

**補足（事実）:** E2 の `create_db_writer` と同型の factory は、外部 API 側には未導入。

---

## 4. Batch × 外部依存マトリクス（事実）

| Batch | 主な外部依存 | CLI 非 demo の現状 | 備考 |
| ----- | ------------ | ------------------ | ---- |
| 001 genre_sync | 楽天 + Object Storage | Rakuten HTTP 未配線 → exit 3 | `RAKUTEN_APPLICATION_ID` 必須チェックあり |
| 002 ranking_snapshot | 楽天 + Object Storage | 同上 | |
| 003 item_pseudo_diff | 楽天 + Object Storage | 同上 | |
| 004 item_recheck | 楽天 + Object Storage | 同上 | |
| 005 raw_staging | Object Storage + DB 読取 | Storage/DB 読取未配線 → exit 3 | |
| 006〜008 / 009〜017（DB 中心） | 主に DB（E2） | DbWriter 配線済み。読取 SELECT / 外部 API は別 | 本 Epic の主対象は外部 I/O 側 |
| 010 item_semantic | Semantic adapter（LLM stub） | DB 読取未配線メッセージ | LLM 本接続は Human 確認 |
| 015 item_embedding | Embedding adapter | DB 読取未配線メッセージ | IF-EXT-005 本接続が中心候補 |
| 018 offline_evaluation | Reco IF 等 | **E3 除外** | E0 §10 |
| 019 feedback_analysis | （物理未整備含む） | **E3 除外** | |

---

## 5. env / secret 名（値なし・事実）

`apps/batch` settings / KEYS から確認できる代表名（**値は記載しない**）。

| 環境変数名 | 用途（推論含む） | E3 での扱い（案） |
| ---------- | ---------------- | ----------------- |
| `RAKUTEN_APPLICATION_ID` | 楽天 API 認証 | 本接続時必須 |
| `RAKUTEN_ACCESS_KEY` | 楽天 API 認証（設定に存在） | 要仕様突合 |
| `OPENAI_API_KEY` | Embedding / LLM | Embedding 本接続時。ログ禁止 |
| `DATABASE_URL` | DB（E2） | 本 Epic 主対象外（併用可） |
| Object Storage 系 | bucket / endpoint 等 | 実装・docs 突合が後続 Task |

**禁止（事実・方針）:** 実 API キー・token・`.env` 実値を docs / Issue / PR / ログ / commit に書かない。

---

## 6. stub 種別（事実）

| 種別 | 代表 | 意味 |
| ---- | ---- | ---- |
| A. Scaffold client | Rakuten / Embedding / Storage | 外部 I/O なし。呼出記録のみ or 疑似応答 |
| B. Scaffold adapter | Semantic / Embedding adapter | job 層が使う生成境界。実 API 非呼出 |
| C. CLI exit 3 | 多数の `__main__.py` | 非 demo で本接続未実装を明示 |
| D. E2 DbWriter | `create_db_writer` | DB 書込は切替可。外部 API とは独立 |

---

## 7. 後続 Task 分割案（推論）

| 順 | 推奨 Task | 内容 | Human 関与 |
| -- | --------- | ---- | ---------- |
| T1 | **本 Task（棚卸し）** | 本 docs | Review |
| T2 | Rakuten HTTP client | `HttpRakutenApiClient` + `create_rakuten_client`（Scaffold 切替）。001〜004 CLI 配線 | Review / secret |
| T3 | Embedding client | OpenAI Embeddings 本接続 + Scaffold 切替。015 adapter 配線 | Review / secret |
| T4 | Object Storage client | 実 Storage client（範囲は棚卸し結果で確定）+ 001〜005 配線 | Review |
| T5 | UT / 境界 | Protocol 互換・scaffold 回帰・secret マスク。live は明示フラグのみ | — |

**推奨着手順（推論）:** T1 → **T2（楽天）** → T3（Embedding）→ T4（Storage）→ T5。

**Semantic LLM:** MVP は Rule-first。本接続を E3 に含めるかは Human 確認（推奨: **含めない / 後続**）。

---

## 8. Human 確認事項

| No | 確認事項 | 推奨案 |
| -- | -------- | ------ |
| 1 | 着手順 | **楽天 → Embedding → Object Storage** |
| 2 | Semantic LLM 本接続を E3 に含めるか | **含めない**（Rule-first 維持） |
| 3 | CI / 既定実行での live 呼出 | **既定 off**。明示フラグ + secret がある時のみ |
| 4 | Object Storage 実装先 | 既存 Scaffold 契約を保ち S3 互換等を後続で選定 |

---

## 9. E0 / E2 との関係（事実）

| 文書 | 関係 |
| ---- | ---- |
| バッチ横串整合・本実装ギャップ一覧 | E0 正本。§10 で E3=外部接続 |
| バッチIF-DB・DDL本実装ギャップ一覧 | E2 正本。DB stub 解除は完了。本 Epic は外部 I/O |

---

## 10. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-24 | 初版（E3 inventory / #1599） |
