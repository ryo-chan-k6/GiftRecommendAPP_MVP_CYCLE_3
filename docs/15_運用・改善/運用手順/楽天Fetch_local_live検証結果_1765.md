# BATCH-001〜004 local live 検証結果（#1765）

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連Issue | #1765（親Epic #1763） |
| 前提Decision | [2026-07-30-rakuten-fetch-ops-policy](../../../ai-logs/human-decisions/2026-07-30-rakuten-fetch-ops-policy.md) / [2026-07-31-rakuten-fetch-mvp-fetch-plan](../../../ai-logs/human-decisions/2026-07-31-rakuten-fetch-mvp-fetch-plan.md) |
| 記録日 | 2026-07-31 |
| MVP対象ジャンル | `100000` / `100003` / `100004` / `100005`（fetch_plan承認済み） |
| 実楽天HTTP | **未実施**（`fetch_plan` は承認済み。実行はHuman環境・secret・監視のもとで段階実施する） |

secret・token・APIキー実値は本ドキュメントに含めない。

---

## 2. 実装したノブ（CLI）

| Batch | ノブ | 既定 / 採択との関係 |
| ----- | ---- | ------------------- |
| BATCH-002 | `--max-pages` | 既定 **1**（Decision 維持） |
| BATCH-003 | `--pages-per-run` | smoke 既定 **1**。通常継続は **60** を CLI 指定 |
| BATCH-003 | `--cursors-per-run` | CLI 既定 **1** |
| BATCH-003 | `--wall-clock-seconds` | 0=無効。通常継続目安 2700（45分） |
| BATCH-003 | `--hits` | 既定 30 |
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

結果（2026-07-31）: **86 passed**

確認できた振る舞い（事実）:

| 観点 | 結果 |
| ---- | ---- |
| Run予算到達後も cursor は `active` のまま次 page を保持 | UT で確認 |
| `rate_limited`（GRS-EXT-102）→ `paused`、page 非進行、`api_call_log.status=rate_limited` | BATCH-003/004 UT で確認 |
| 空 Items / `pageCount` 到達 → `exhausted`（実装内部名 `completed`）。Run予算停止とは区別 | UT で確認 |
| `cursors_per_run` で着手 cursor 数を制限 | UT で確認 |

---

## 4. local live（実楽天HTTP）— 未実施理由と手順案

### 4.1 fetch_plan（承認済み・2026-07-31）

[2026-07-31-rakuten-fetch-mvp-fetch-plan](../../../ai-logs/human-decisions/2026-07-31-rakuten-fetch-mvp-fetch-plan.md) で承認済み。

| 項目 | 値 |
| ---- | ---- |
| MVP対象ジャンルID | `100000` / `100003` / `100004` / `100005` |
| BATCH-001 | 4 ID起点・直下 `children` まで。初回1 ID |
| BATCH-002 | 4 ID。初回1 ID × `max_pages=1` |
| BATCH-003 genre | 4 ID。初回1 ID |
| keyword | なし |
| update_sort | 初回オフ（通常継続からオン可） |
| ranking_supplement | オン（backlog時のみ） |
| 初回低値 | 1ジャンル / 1 route × 1 cursor × 1ページ / `hits=3` |

実HTTPはHuman環境・secret投入・監視のもとで実施する（実行タイミングは実行時Human判断）。

### 4.2 推奨 smoke 手順（低値・secretなしログ）

承認済み `fetch_plan` に沿って、local で以下を段階実行する（例は genre `100000`）。

1. BATCH-001 `--genre-ids 100000 --live-rakuten`（egress 一致時のみ。children同期を確認）
2. BATCH-002 `--genre-ids 100000 --max-pages 1 --live-rakuten`
3. BATCH-003 `--genre-ids 100000 --pages-per-run 1 --cursors-per-run 1 --hits 3 --max-qps 1 --live-rakuten`
4. 問題なければ BATCH-003 を4 IDへ拡大 → `--pages-per-run 10` → 通常 `60` / `--wall-clock-seconds 2700`
5. BATCH-004 `--max-items 100 --max-qps 1 --live-rakuten`

GHA 葉 workflow から楽天HTTPは呼ばない（当面 local のみ）。

---

## 5. 残リスク / Human Review観点

| 項目 | 内容 |
| ---- | ---- |
| fetch_plan | 承認済み（2026-07-31）。実HTTPの実行タイミング・secret投入はHuman環境で実施 |
| 監視閾値抵触 | §5.3.5 抵触時の打ち切り／予算縮小は実行時Human判断 |
| Project Status | bot token に `read:project` が無く Status 更新はHuman側で実施が必要な場合あり |
| GHA | 楽天 scaffold 維持。変更していない（整合のみ） |
| #1607 / schedule | out of scope |

---

## 6. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-31 | 初版。実装ノブ・UT結果・実HTTP未実施理由を記録（#1765） |
| 2026-07-31 | fetch_plan承認（4ジャンル・children展開・keyword無し）を反映。smoke手順を具体化 |
| 2026-07-31 | #1775 AI Review対応: §3 の `exhausted` / `completed` 表記を整理 |
