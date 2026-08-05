# fetch_plan拡大 第1波 段階収集結果（#1847）

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連Issue | #1847（親Epic #1843。Decision #1844 / 手順 #1846） |
| 前提 | [拡大候補 Decision](../../../ai-logs/human-decisions/2026-08-04-batch-fetch-plan-expansion-candidates.md)（`decided`・案B） / [第1波1ジャンル手動実行手順](./fetch_plan拡大_第1波_1ジャンル手動実行手順.md) |
| 記録日 | 2026-08-05 |
| 実行主体 | **Human**（`--live-rakuten`）。AI は結果docs同期・選定/反映阻害時の最小修正（#1849〜#1856）・PR/Review |
| スコープ実績 | 案B第1波 **6ID** の BATCH-003 genre 走査完了 + BATCH-002 Ranking（各 `max_pages=1`）+ staging→item 反映完了 |

secret・token・APIキー・接続文字列実値は記載しない。個別 `pipeline_batch_run_id` / `job_run_id` の全一覧は Human 端末ログに保持し、本docsへは代表値・集計のみ載せる。

---

## 2. 実行方針（遵守確認）

| 観点 | 実績 |
| ---- | ---- |
| ジャンル単位 | **1本ずつ**（`--genre-ids` に案B IDを並べない） |
| Item / Ranking | **別 Run・別タイミング**（親 daily 先頭からの 002→003 連続は未使用） |
| BATCH-003 優先 | Item（`--from-step item_pseudo_diff`）を先に完了後、Ranking 葉を実行 |
| 同時楽天 live | 1本（手順どおり） |
| AI `--live-rakuten` | **なし**（Human のみ） |
| 定常 crontab（#1811 / #1818） | **変更なし** |
| GHA 楽天 live / #1607 | **対象外維持** |

---

## 3. BATCH-003（genre）走査結果

承認スコープ（MVP 4 + 案B 6）の `fetch_cursor`（`cursor_type=genre`）を 2026-08-05 時点で確認。

| wave | external_genre_id | genre_name（Decision） | cursor_status | page | 備考 |
| ---- | ----------------: | ---------------------- | ------------- | ---: | ---- |
| MVP | 100000 | （既存） | exhausted | 1 | 早期 exhausted |
| MVP | 100003 | （既存） | exhausted | 1 | 早期 exhausted |
| MVP | 100004 | （既存） | exhausted | 1 | 早期 exhausted |
| MVP | 100005 | （既存） | exhausted | 100 | API 同一クエリ上限側 |
| 第1波 | 101381 | カタログギフト・チケット | exhausted | 100 | 推奨最初の1ID |
| 第1波 | 551167 | スイーツ・お菓子 | exhausted | 100 | |
| 第1波 | 510901 | 日本酒・焼酎 | exhausted | 100 | |
| 第1波 | 216129 | ジュエリー・アクセサリー | exhausted | 100 | |
| 第1波 | 558944 | キッチン用品・食器・調理器具 | exhausted | 100 | 初回に他 genre cursor が割り込んだ事例あり（後述） |
| 第1波 | 100939 | 美容・コスメ・香水 | exhausted | 100 | |

**事実:** 案B 6ID および MVP 4ID の genre カーソルはすべて `exhausted`。`active` の genre カーソルは 0。

**推論:** 第1波 6ID が `page=100` で exhausted しているのは、楽天 ItemSearch の同一クエリ最大100ページに到達した完了であり、ジャンル実在数がそれを超える場合の取り切り保証ではない（運用方針 §5.3.2）。

### 3.1 代表ノブ（Item Run）

| 項目 | 値 |
| ---- | ---- |
| 起動 | `local_daily_orchestrator.sh --live-rakuten --from-step item_pseudo_diff` |
| `pages_per_run` | 主に **60**（通常継続。一部で120等の加速的指定あり） |
| `max_qps` | **1** |
| `cursors_per_run` | 既定 **1**（明示省略または1） |

### 3.2 運用上の注意（実績）

| 事象 | 扱い |
| ---- | ---- |
| `cursors_per_run=1` 時、他 genre の `active` 残が先に消費される | `558944` 起動時に `100004` が消化され、対象が未進行のまま終わった。再実行で解消 |
| BATCH-005 同一 `image_url` 重複 upsert | #1851 / PR #1852 で修正後に継続 |
| BATCH-006 `staging_item.diff_status` が live 未同期 | #1853 / PR #1854 で修正。既存分は Human がバックフィル |
| BATCH-006/007 先頭スキャン上限 | 反映作業中に顕在化。#1855 / PR #1856 で修正（結果記録時点で Epic 反映済み） |
| BATCH-008 error_code / Diff 範囲 | #1849 / PR #1850 で修正 |

---

## 4. BATCH-002（Ranking）結果

葉 `batch.application.ranking_snapshot` を **ジャンル1本・`--max-pages 1`** で別起動（Human）。

| external_genre_id | ranking_snapshot 件数（当該ID） | last fetched_at（UTC） |
| ----------------: | -----------------------------: | ---------------------- |
| 101381 | 1 | 2026-08-04 16:23:37 |
| 551167 | 1 | 2026-08-04 16:28:07 |
| 510901 | 1 | 2026-08-04 16:28:21 |
| 216129 | 1 | 2026-08-04 16:28:39 |
| 558944 | 1 | 2026-08-04 16:28:53 |
| 100939 | 1 | 2026-08-04 16:29:09 |

**事実:** 案B 6ID すべてに Ranking スナップショットが1件以上存在する。本記録時点で Ranking HTTP 400 によるスキップは報告されていない（全ID成功扱い）。

**事実（副次）:** `fetch_cursor` に `ranking_supplement` が残存（例: active 約200件台）。BATCH-003 の後続 Run で消化する想定。本 Task では全件取り切りを完了条件にしない。

---

## 5. staging → item 反映結果（2026-08-05 確認）

| 指標 | 件数 |
| ---: | ---: |
| `staging_item` 行 | 20,585 |
| staging 商品コード（distinct） | 17,603 |
| staging `diff_status` NULL | **0** |
| `item` | 17,606 |
| `item`（`active_status=active`） | 17,605 |
| staging にあって item にないコード | **0** |

**事実:** 第1波収集で staging に載った商品コードは、item 本体へ反映済み（差分0）。

**補足:** item 件数が staging コードよりわずかに多い（+3）。staging 以外経路や重複解消後の残差として説明可能であり、本完了判定（staging→item 漏れ0）には影響しない。

---

## 6. 切替ゲート記録

手順 §6 のゲートに対する本収集の扱い。

| No | ゲート | 本収集での扱い |
| --: | ------ | -------------- |
| 1 | 直近 Run が致命失敗していない | 途中で BATCH-005/006/007/008 阻害あり → 修正PR後に再開。最終的に案B 6ID 完走 |
| 2 | 429 / `rate_limited` の再発がない | Human 報告ベースで本記録に **429連続なし**（個別ログは端末保持） |
| 3 | DB / Raw 容量に余裕 | hard 停止には至らず完走（絶対容量値は本docsに書かない） |
| 4 | 他の楽天 live が動いていない | 1本運用を維持 |
| 5 | 次IDが案B内 | 案B 6ID まで実施。第2波は **本 Task 外**（別 Decision） |

---

## 7. 監視・残課題

| 区分 | 内容 |
| ---- | ---- |
| 事実 | genre cursor はスコープ10IDすべて exhausted |
| 事実 | staging 未判定0・staging→item 漏れ0 |
| 事実 | Ranking は案B 6ID 取得済み |
| 残（運用） | `ranking_supplement` active 残の消化（BATCH-003 継続） |
| 残（設計） | 同一クエリ page=100 天井を超える拡充が必要なら細分化等は **Human 別判断** |
| 残（Epic） | 意味連鎖（`--run-meaning`）は本結果の対象外 |
| 完了済み阻害対応 | #1849/#1850, #1851/#1852, #1853/#1854, #1855/#1856 |

---

## 8. 結論

- 第1波（案B 6ID）の **Human local live**（BATCH-003 genre 走査 + BATCH-002 Ranking）と **staging→item 反映**は、本記録時点で完了扱いにできる。
- AI は `--live-rakuten` を実行していない。定常 crontab / GHA 楽天 live は変更していない。
- 次の本線候補は、意味連鎖の Human 判断、または `ranking_supplement` 消化の継続運用。

---

## 9. 関連資料

| 資料 | 用途 |
| ---- | ---- |
| [拡大候補 Decision](../../../ai-logs/human-decisions/2026-08-04-batch-fetch-plan-expansion-candidates.md) | 案B正本 |
| [第1波1ジャンル手動実行手順](./fetch_plan拡大_第1波_1ジャンル手動実行手順.md) | 起動手順 |
| [楽天Fetch運用方針](./楽天Fetch運用方針.md) §11.6 | 運用枠 |
| [BATCH-006 sync 修正](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/pull/1854) | live diff_status 同期 |
| [選定スキャン上限解消](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/pull/1856) | 006/007 先頭5000打ち切り解消 |

---

## 10. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-08-05 | 初版（#1847）。案B 6ID の 003/002/item反映結果と切替ゲートを正本化 |
