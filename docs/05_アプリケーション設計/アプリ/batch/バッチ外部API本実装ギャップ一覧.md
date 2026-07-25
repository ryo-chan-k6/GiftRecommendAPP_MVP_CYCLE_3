# バッチ外部API本実装ギャップ一覧

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | E3 棚卸し正本（docs） |
| 対象 | 楽天 / Embedding / Object Storage / Semantic（LLM）× BATCH-001〜017 |
| 作成日 | 2026-07-24 |
| 更新日 | 2026-07-25（T4 + #1614 / #1617。DB SELECT 後続は #1623） |
| 関連 Epic | [#1598](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1598) / [#1614](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1614) / 読取後続 [#1623](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1623) |
| 関連 Task | [#1599](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1599)（T1） / [#1610](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1610)（T3） / [#1612](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1612)（T4） / [#1617](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1617)（Storage live・リリース準備） |
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
| Rakuten client | `HttpRakutenApiClient` + `create_rakuten_client`（**live 既定 off** → Scaffold） |
| Rate Limiter（MOD-BATCH-008） | `ExternalApiRateLimiter`（プロセス内・常用 QPS=**2** / ハードキャップ 10）。live HTTP に配線 |
| Embedding client | `HttpEmbeddingClient` + `create_embedding_client`（**live 既定 off** → Scaffold） |
| Object Storage | `S3CompatibleObjectStorageClient` + `create_object_storage_client`（**live 既定 off** → Scaffold） |
| Semantic 生成 | `ScaffoldItemSemanticAdapter`（Rule-first / LLM 非呼出） |
| CLI 非 `--scaffold-demo` | 001〜004: `--live-rakuten` 必須。`--live-object-storage` で Storage HTTP（未指定時 Scaffold）。015 Embedding / 005 Storage live 可だが DB 読取は未配線 → exit 3 |
| E2 との関係 | DbWriter / 代表 UPSERT は利用可能。外部 I/O は楽天 + Embedding + Object Storage（各明示 live） |

---

## 3. 外部境界の現状（事実）

| 境界 | Protocol / 入口 | Scaffold 実装 | 実 client | factory 切替 |
| ---- | --------------- | ------------- | --------- | ------------ |
| 楽天 API | `RakutenApiClient` | `ScaffoldRakutenApiClient` | `HttpRakutenApiClient` | `create_rakuten_client`（live 既定 off + Rate Limiter） |
| External API Rate Limiter | `ExternalApiRateLimiter` | （制御なし = Scaffold 相当） | `ExternalApiRateLimiter` | `create_external_api_rate_limiter` / live factory 既定 on |
| Embedding（IF-EXT-005） | `EmbeddingClient` | `ScaffoldEmbeddingClient` | `HttpEmbeddingClient` | `create_embedding_client`（live 既定 off） |
| External AI（汎用） | `ExternalAiClient` | `ScaffoldExternalAiClient` | **なし** | **なし** |
| Object Storage | `ObjectStorageClient` | `ScaffoldObjectStorageClient` | `S3CompatibleObjectStorageClient` | `create_object_storage_client`（live 既定 off） |
| Item Semantic 生成 | adapter（batch 内） | `ScaffoldItemSemanticAdapter` | **なし**（LLM） | **なし** |
| Item Embedding 生成 | adapter（batch 内） | `ScaffoldItemEmbeddingAdapter` | `EmbeddingClient` 注入（Http 可） | `--live-embedding` / `BATCH_EMBEDDING_LIVE` |

**補足（事実）:** 楽天 / Embedding / Object Storage いずれも factory（live 既定 off）導入済み。005 等の DB SELECT 本配線は [#1623](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1623) / [バッチDB読取・SELECT本実装ギャップ一覧](./バッチDB読取・SELECT本実装ギャップ一覧.md)。

---

## 4. Batch × 外部依存マトリクス（事実）

| Batch | 主な外部依存 | CLI 非 demo の現状 | 備考 |
| ----- | ------------ | ------------------ | ---- |
| 001 genre_sync | 楽天 + Object Storage | `--live-rakuten` 必須。Storage は `--live-object-storage` で HTTP（未指定 Scaffold） | `RAKUTEN_*` + 任意 `OBJECT_STORAGE_*` |
| 002 ranking_snapshot | 楽天 + Object Storage | 同上 | |
| 003 item_pseudo_diff | 楽天 + Object Storage | 同上 | |
| 004 item_recheck | 楽天 + Object Storage | 同上（seed 空時は 0 件成功可） | DB SELECT seed は未実装 |
| 005 raw_staging | Object Storage + DB 読取 | Storage live 可。DB 読取未配線 → exit 3 | |
| 006〜008 / 009〜017（DB 中心） | 主に DB（E2） | DbWriter 配線済み。読取 SELECT / 外部 API は別 | 本 Epic の主対象は外部 I/O 側 |
| 010 item_semantic | Semantic adapter（LLM stub） | DB 読取未配線メッセージ | LLM 本接続は Human 確認 |
| 015 item_embedding | Embedding adapter | DB 読取未配線 → exit 3。`--scaffold-demo --live-embedding` で HTTP 煙 | IF-EXT-005 client は T3 完了 |
| 018 offline_evaluation | Reco IF 等 | **E3 除外** | E0 §10 |
| 019 feedback_analysis | （物理未整備含む） | **E3 除外** | |

---

## 5. env / secret 名（値なし・事実）

`apps/batch` settings / KEYS から確認できる代表名（**値は記載しない**）。

| 環境変数名 | 用途（推論含む） | E3 での扱い（案） |
| ---------- | ---------------- | ----------------- |
| `RAKUTEN_APPLICATION_ID` | 楽天 API 認証 | `--live-rakuten` 時必須 |
| `RAKUTEN_ACCESS_KEY` | 楽天 API 認証 | `--live-rakuten` 時必須 |
| `BATCH_RAKUTEN_LIVE` | live 切替（`1`/`true`/`yes`/`on`） | CLI `--live-rakuten` と同等 |
| `RAKUTEN_EXPECTED_EGRESS_IP` | live 検証時の接続元 IP 照合 | ハーネス必須（不一致時は HTTP しない） |
| `RAKUTEN_MAX_QPS` | クライアント常用 QPS | 既定 **2**（ハードキャップ 10。旧目標 8 は常用外）。別名 `BATCH_EXTERNAL_API_MAX_QPS` |
| `RAKUTEN_MIN_INTERVAL_MS` | 呼出最小間隔（ms） | 任意。未設定時は QPS から算出。ハードキャップ未満（過短）は拒否 |
| `OPENAI_API_KEY` | Embedding / LLM | `--live-embedding` 時必須。ログ禁止 |
| `BATCH_EMBEDDING_LIVE` | Embedding live 切替（`1`/`true`/`yes`/`on`） | CLI `--live-embedding` と同等 |
| `DATABASE_URL` | DB（E2） | 本 Epic 主対象外（併用可） |
| `OBJECT_STORAGE_BUCKET` | Raw 保存先 bucket | live 時の repos bucket |
| `OBJECT_STORAGE_ENDPOINT` | S3 互換 endpoint | `--live-object-storage` 時必須 |
| `OBJECT_STORAGE_ACCESS_KEY` / `OBJECT_STORAGE_SECRET_KEY` | Storage 認証 | live 時必須。ログ禁止 |
| `BATCH_OBJECT_STORAGE_LIVE` | Storage live 切替 | CLI `--live-object-storage` と同等 |

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
| T2 | Rakuten HTTP client（**完了 / #1601 / #1602**） | `HttpRakutenApiClient` + `create_rakuten_client`（Scaffold 切替）。001〜004 CLI 配線 | Review / secret |
| T2b | Rakuten live 疎通（**完了 / #1603 / Adjust**） | openapi endpoint 移行後、genre / ranking / item_search 成功。**常用 QPS=2**・IP 必須 | Review / secret |
| T2c | External API Rate Limiter（**完了 / #1605 / #1608** / `MOD-BATCH-008`） | 常用 QPS=**2**（ハードキャップ 10）。`HttpRakutenApiClient` 送信前 + 429 backoff | Review |
| T2d | Genre/Ranking/endpoint 正式反映（**完了 / #1606 / #1609**） | Genre `genre` キー / Ranking period 分離 / 現行 endpoint を正式 Batch・外部連携・adapter へ | Review |
| T3 | Embedding client（**完了 / #1610**） | `HttpEmbeddingClient` + `create_embedding_client`。015 `--live-embedding` 配線 | Review / secret |
| T4 | Object Storage client（**完了 / #1612**） | `S3CompatibleObjectStorageClient` + factory。001〜005 `--live-object-storage` | Review / secret |
| T5 | UT / 境界 | Protocol 互換・scaffold 回帰・secret マスク。live は明示フラグのみ | — |

**推奨着手順（推論）:** T1 → T2（楽天）→ **T2b（live 疎通）** → **T2c（Rate Limiter）** / **T2d（正式契約反映）** → T3（Embedding）→ T4（Storage）→ T5。

**Semantic LLM:** MVP は Rule-first。本接続を E3 に含めるかは Human 確認（推奨: **含めない / 後続**）。

**T2b 補足（事実）:** 旧 `app.rakuten.co.jp` endpoint では新 credential（UUID + `pk_`）が `specify valid applicationId`。`openapi.rakuten.co.jp` 系へ移行後に 3 API 成功疎通。短時間連続実行で ranking 429 を観測。判定 **Adjust**。

### 7.1 Backlog（未検討・Human 決定）

| ID | 内容 | 状態 |
| -- | ---- | ---- |
| BL-RAKUTEN-EGRESS-PROD | 本番（および将来の固定 egress 実行基盤）の接続元 IP 登録・NAT / self-hosted 等の設計 | **Backlog / #1607**。2026-07-24 Human: 現時点では検討しない。human-led / no-branch |

参照: `ai-logs/human-decisions/2026-07-24-rakuten-api-qps-ip-verify-policy.md`

---

## 8. Human 確認事項

| No | 確認事項 | 推奨案 / 状態 |
| -- | -------- | ------------- |
| 1 | 着手順 | **楽天 → Embedding → Object Storage** |
| 2 | Semantic LLM 本接続を E3 に含めるか | **含めない**（Rule-first 維持） |
| 3 | CI / 既定実行での live 呼出 | **既定 off**。明示フラグ + secret がある時のみ（動的 IP のため） |
| 4 | Object Storage 実装先 | **確定**（#1614）: 製品=**Supabase Storage** / 接続=**案 A（S3 互換 + `OBJECT_STORAGE_*`）**。#1612 `S3CompatibleObjectStorageClient` 維持。live 疎通は [#1617](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1617)（リリース準備）local で **Go**（[PoC結果](../../../90_PoC/外部API疎通検証/Supabase_Storage_S3互換疎通検証結果.md)） |
| 5 | 楽天常用 QPS / IP 照合 / Rate Limiter Task 切り | **決定済**（常用 QPS=**2** / IP 必須 / T2c 別 Task） |
| 6 | 本番 egress IP 設計 | **Backlog / #1607**（§7.1）。未検討 |

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
| 2026-07-24 | T2: `HttpRakutenApiClient` / factory / 001〜004 CLI / UT（#1601） |
| 2026-07-24 | T2b: Rakuten live 疎通検証（#1603）。認証失敗により Block |
| 2026-07-24 | Human 決定: 目標 QPS=8、egress IP 照合必須、T2c Rate Limiter 別 Task、本番 egress を Backlog（BL-RAKUTEN-EGRESS-PROD） |
| 2026-07-24 | T2b: openapi endpoint 移行・live 3 API 成功（Adjust）。Genre `genre` キー / Ranking period 扱い / 429 を記録 |
| 2026-07-25 | 常用 QPS を実験結果に基づき **2** へ改訂（旧 8 は常用外）。T2c 設計入力も 2 |
| 2026-07-25 | 後続 Issue 起票: T2c #1605 / T2d #1606 / BL-RAKUTEN-EGRESS-PROD #1607 |
| 2026-07-25 | T2c: `ExternalApiRateLimiter` 実装・Http client 配線・UT（#1605） |
| 2026-07-25 | T2d: Genre/Ranking/endpoint 正式 Batch・外部連携・adapter 反映（#1606） |
| 2026-07-25 | T3: `HttpEmbeddingClient` / factory / 015 `--live-embedding` / UT（#1610） |
| 2026-07-25 | T4: `S3CompatibleObjectStorageClient` / factory / 001〜005 live 配線 / UT（#1612） |
| 2026-07-25 | Object Storage 接続方針 A 確定反映（製品=Supabase Storage / S3 互換）。Epic #1614 / Task #1615 |
| 2026-07-25 | Object Storage S3 互換 live 疎通ハーネス・結果記録（#1617・リリース準備） |
| 2026-07-25 | #1617 再検証: local Supabase で put/get/missing **Go**（案 B 不要） |
| 2026-07-25 | DB SELECT 後続を Epic #1623 / [SELECTギャップ一覧](./バッチDB読取・SELECT本実装ギャップ一覧.md) へ分離（#1624） |
