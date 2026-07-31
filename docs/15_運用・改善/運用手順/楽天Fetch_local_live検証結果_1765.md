# BATCH-001〜004 local live 検証結果（#1765）

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連Issue | #1765（親Epic #1763） |
| 前提Decision | [2026-07-30-rakuten-fetch-ops-policy](../../../ai-logs/human-decisions/2026-07-30-rakuten-fetch-ops-policy.md) / [2026-07-31-rakuten-fetch-mvp-fetch-plan](../../../ai-logs/human-decisions/2026-07-31-rakuten-fetch-mvp-fetch-plan.md) |
| 記録日 | 2026-07-31 |
| MVP対象ジャンル | `100000` / `100003` / `100004` / `100005`（fetch_plan承認済み） |
| 実楽天HTTP | **パターンB実施済み**（local専用 `DATABASE_URL` + local `.env`。Object Storage live も確認済み） |

secret・token・APIキー・egress IP・`DATABASE_URL` 実値は本ドキュメントに含めない。

---

## 2. 実装したノブ（CLI）

| Batch | ノブ | 既定 / 採択との関係 |
| ----- | ---- | ------------------- |
| BATCH-002 | `--max-pages` | 既定 **1**（Decision 維持） |
| BATCH-003 | `--pages-per-run` | smoke 既定 **1**。通常継続は **60** を CLI 指定 |
| BATCH-003 | `--cursors-per-run` | CLI 既定 **1** |
| BATCH-003 | `--wall-clock-seconds` | 0=無効。通常継続目安 2700（45分） |
| BATCH-003 | `--hits` | 既定 30 |
| BATCH-003 | `--no-update-sort` | 初回 smoke / fetch_plan（update_sort=off）向け |
| BATCH-003/004 | `--max-qps` | live 既定 **1**（安全側）。常用 QPS=2 は変更しない |
| BATCH-004 | `--max-items` / GHA `max_items` | 既定 **100**（段階拡張の開始件数。葉 workflow も同値。楽天HTTPは Scaffold 維持） |

`--max-pages`（BATCH-003）は `--pages-per-run` の互換 alias。Run予算でありカタログ深さ打ち切りではない。

---

## 3. unit test（実施済み）

作業ディレクトリ: `apps/batch`

```bash
uv sync --extra dev
uv run pytest \
  tests/unit/application/test_item_pseudo_diff.py \
  tests/unit/application/test_item_recheck.py \
  tests/unit/application/test_ranking_snapshot.py \
  tests/unit/application/test_genre_sync.py \
  -q
```

結果（2026-07-31・パターンB直前）: **87 passed**

確認できた振る舞い（事実）:

| 観点 | 結果 |
| ---- | ---- |
| Run予算到達後も cursor は `active` のまま次 page を保持 | UT で確認 |
| `rate_limited`（GRS-EXT-102）→ `paused`、page 非進行、`api_call_log.status=rate_limited` | BATCH-003/004 UT で確認 |
| 空 Items / `pageCount` 到達 → `exhausted`（実装内部名 `completed`）。Run予算停止とは区別 | UT で確認 |
| `cursors_per_run` で着手 cursor 数を制限 | UT で確認 |
| Genre adapter が openapi `nameJa` を受理 | UT で確認 |

---

## 4. local live（パターンB）— 実施結果

### 4.1 前提

| 項目 | 内容 |
| ---- | ---- |
| 方式 | パターンB（local専用 Postgres + 実楽天HTTP） |
| Object Storage | live（`--live-object-storage`。PUT/GET 確認済み） |
| 事前API verify | `rakuten_live_verify.py --live-rakuten` → success=4 / egress_matched=True（Human環境） |

### 4.2 fetch_plan（承認済み・2026-07-31）

| 項目 | 値 |
| ---- | ---- |
| MVP対象ジャンルID | `100000` / `100003` / `100004` / `100005` |
| BATCH-001 | 4 ID起点・直下 `children` まで。初回1 ID |
| BATCH-002 | 4 ID。初回1 ID × `max_pages=1` |
| BATCH-003 genre | 4 ID。初回1 ID |
| keyword | なし |
| update_sort | 初回オフ（`--no-update-sort`） |
| ranking_supplement | オン（BATCH-002 backlog消費） |
| 初回低値 | 1ジャンル / 1 route × 1 cursor × 1ページ / `hits=3` |

### 4.3 実施コマンド（secretなし）

作業ディレクトリ: `apps/batch`（repo root で `set -a && source .env && set +a`）

| Batch | 結果 | 備考 |
| ----- | ---- | ---- |
| BATCH-001 `--genre-ids 100000 --live-rakuten` | **succeeded** | 親+直下children 7行を `external_genre` / `staging_genre` へ反映 |
| BATCH-001 `--genre-ids 100005 --live-rakuten` | **succeeded** | Ranking対象ジャンルを同期 |
| BATCH-002 `--genre-ids 100005 --max-pages 1 --live-rakuten` | **succeeded** | `100000`/`100003`/`100004` は Ranking API が HTTP 400 |
| BATCH-003 ranking_supplement / genre `100003`（`--pages-per-run 1 --cursors-per-run 1 --hits 3 --max-qps 1 --no-update-sort`） | **succeeded** | pages=1 / budget_stopped=True |
| BATCH-004 `--max-items 1 --external-item-codes <実itemCode> --max-qps 1 --live-rakuten` | **succeeded** | local `item` の test-fixture は実API非対象のため実コード指定 |

### 4.4 実施中に直した実装ギャップ（事実）

| ギャップ | 対応 |
| -------- | ---- |
| Genre live payload が `nameJa`（旧 adapter は `jaName`/`genreName` のみ） | adapter が `nameJa` を優先受理 |
| `raw_product_metadata` へ非DDL列（`genre_id` 等）を書いていた | DDL列のみ INSERT（001/002/003/004） |
| `staging_genre.raw_metadata_id` / `is_leaf` / `staged_at` 不足 | save_raw が UUID を返し staging/external へ配線。直下 children 展開 |
| `staging_ranking_signal` に非採用の `source` 列を書いていた | DDL列へ修正。`lastBuildDate` を timestamptz 化 |
| BATCH-003 が DB 上の active `ranking_supplement` を読んでいなかった | `list_active_cursors` が DbReader から読込 |
| update_sort が genreId 未設定で ItemSearch 400 | CLI `--no-update-sort`（fetch_plan 初回オフ） |
| BATCH-004 `fetch_cursor` に非DDL列 `page`/`scope` を書いていた | `cursor_value` JSON + `update_rows` に修正 |

### 4.5 Ranking 対象ジャンル（実測）

| genreId | Ranking API |
| ------- | ----------- |
| `100000` / `100003` / `100004` | HTTP 400（wrong_parameter） |
| `100005` / `100371` / `100283` | 成功（Items あり） |

推論: MVP 4 IDのうち Ranking 初回 smoke は **`100005`** が妥当。`100000` 配下の `100003`/`100004` は Genre 同期の children としては有効。

### 4.6 Object Storage live 再smoke（2026-07-31）

`--live-rakuten --live-object-storage` で BATCH-001〜004 を再実行した。

#### 第1回（失敗）

| 項目 | 結果 |
| ---- | ---- |
| PUT | **失敗** `GRS-RAW-001` / HTTP 400 / `Project not specified.` |
| 原因 | local `.env` の endpoint が `.env.example` プレースホルダのまま |

#### 第2回（`.env` 実値投入後）

| Batch | 結果 | 備考 |
| ----- | ---- | ---- |
| BATCH-001 `100000` / `100005` | **succeeded** | `storage_backend=http` |
| BATCH-002 `100005` | **succeeded**（再実行） | 初回は同一観測キー再INSERTで unique 違反。snapshot get-or-create を冪等化して再成功 |
| BATCH-003 genre `100003` 低値 | **succeeded** | pages=1 / budget_stopped=True |
| BATCH-004 実 itemCode ×1 | **succeeded** | |
| Raw GET 検証 | **OK** | 最新の `genre_search` / `item_ranking` / `item_search` object を Storage から GET 200 |

---

## 5. 残リスク / Human Review観点

| 項目 | 内容 |
| ---- | ---- |
| Object Storage live | 実値投入後の再smokeで PUT/GET 確認済み（local） |
| update_sort | CLI off は追加済み。オン時の genreId/keyword 必須条件の実装妥当性は要確認 |
| Ranking対象 | fetch_plan「4 ID」と Ranking API 実測の差分。Human判断で対象整理が必要になり得る |
| `phase`=`priority` | DDL phase 未マッピング（in-memoryのみ。DB phase_log は skip） |
| 監視閾値抵触 | §5.3.5 抵触時の打ち切り／予算縮小は実行時Human判断 |
| Project Status | bot token に `read:project` が無く Status 更新はHuman側で実施が必要な場合あり |
| GHA | 楽天 scaffold 維持。変更していない |
| #1607 / schedule | out of scope |

---

## 6. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-31 | 初版。実装ノブ・UT結果・実HTTP未実施理由を記録（#1765） |
| 2026-07-31 | fetch_plan承認（4ジャンル・children展開・keyword無し）を反映。smoke手順を具体化 |
| 2026-07-31 | #1775 AI Review対応: §3 の `exhausted` / `completed` 表記を整理 |
| 2026-07-31 | パターンB実施結果・adapter/DDLギャップ修正・Ranking対象実測を追記 |
| 2026-07-31 | Object Storage live 再smoke試行。endpoint プレースホルダにより PUT 400 で未完了を記録 |
| 2026-07-31 | `.env` 実値投入後に Object Storage live 再smoke成功。BATCH-002 snapshot 冪等化を追記 |
