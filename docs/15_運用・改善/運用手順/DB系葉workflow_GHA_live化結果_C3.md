# DB系葉workflow GHA live化結果（C3）

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連 Epic | [#1750](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1750) |
| 関連 Task | [#1751](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1751) |
| 対象 | BATCH-009 / 011 / 012 / 013 / 014 / 016 |
| 環境 | GitHub Environment `stg` |
| DB Secret | `STG_DATABASE_URL` を job env `DATABASE_URL` へ割り当て |
| 記録日 | 2026-07-30 |

本結果に secret、token、DB接続文字列の実値は含めない。

## 2. Phase A: 現状調査

変更前は、対象6葉が `--scaffold-demo` を指定し、`job_run_id` の未指定時に
`gha-<run_id>-<run_attempt>` 形式の非UUIDを生成していた。

meaning複合 `batch-item-meaning-generation.yml` は、共有
`pipeline_batch_run_id` を BATCH-009〜015 の各 `job_run_id` として渡していた。
この構造は、pipeline IDと葉の tracker / `batch_run_log` PKを分離する方針と
一致していなかった。

既liveの BATCH-005〜008 / 017 では、次のパターンを使用していることを確認した。

- jobに `environment: stg` を指定する
- `DATABASE_URL: ${{ secrets.STG_DATABASE_URL }}` を設定する
- 葉の `job_run_id` を新規UUIDとして生成する
- pipeline IDと葉の `job_run_id` を分離する

## 3. Phase B: 葉live化

009 → 011 → 012 → 013 → 014 → 016 の順で、次を反映した。

- `--scaffold-demo` を削除
- `environment: stg` を追加
- `STG_DATABASE_URL` を `DATABASE_URL` へ割り当て
- `job_run_id` の既定値を新規UUIDへ変更
- step名とコメントをstg live経路へ同期

BATCH-016末尾のBATCH-017もlive経路へ揃え、017の新規 `job_run_id` と
集計対象である016の `job_run_id` を分離した。010 / 015のAI経路は変更していない。

## 4. Phase C: meaning複合整合

`batch-item-meaning-generation.yml` では、共有 `pipeline_batch_run_id` を
各葉の `job_run_id` として渡さないよう変更した。

- 009 / 011〜014: 各live葉で新規UUIDを生成
- 010 / 015: scaffoldを維持し、各葉の既定Run IDを使用
- 017: 集計対象として共有 `pipeline_batch_run_id` のみ受け取り、
  自身の `job_run_id` は新規UUIDを生成

`batch-retry-failed-items.yml` でも、live化した011〜014へ共有Run IDを渡さず、
各葉で新規UUIDを生成するよう整合した。

## 5. Phase D: 既live葉の回帰確認

BATCH-005 / 006 / 007 / 008 / 017 のworkflowに差分がないことを確認した。
既存の `environment: stg`、`STG_DATABASE_URL`、UUID生成、pipeline ID分離は
変更していない。

次のout of scopeにも差分はない。

- BATCH-001〜004の楽天live経路
- BATCH-010 / 015のAI live経路
- 親workflowの `on.schedule`
- BATCH-018 / 019
- OpenAPI / Orval / generated
- DDL / migration

## 6. Phase E: stg手動検証

Human判断（2026-07-30）:

1. `max_items=1` でのstg書込を許可
2. 低件数・葉/複合単位の手動のみ許容
3. Environment `stg` required reviewers は解除済み（承認待ちなし）
4. BATCH-016末尾→017接続は維持

### 6.1 実施サマリ

| 項目 | 内容 |
| ---- | ---- |
| ref | `feature/task-1751-db-leaf-workflow-live` (`30b79967`) |
| 実施時刻 | 2026-07-30（UTC） |
| 判定 | **FAIL**（workflow配線は到達、stg DB接続で失敗） |

| Workflow | inputs | Run URL | status | conclusion |
| -------- | ------ | ------- | ------ | ---------- |
| Batch Item Meaning Generation | `max_items=1`, `source=rakuten` | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30545806388 | completed | failure |
| Batch Distribution Metrics | `trigger_mode=dispatch`, embedding/user_meaning=false | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30545808936 | completed | failure |

### 6.2 Job結果（事実）

#### meaning複合（30545806388）

| Job | conclusion |
| --- | ---------- |
| `resolve-run-id` | success |
| `item_generation_queue / item-generation-queue` | **failure**（step: `Run BATCH-009 live`） |
| `item_semantic` 以降 | skipped（上流 failure） |

#### distribution-metrics（30545808936）

| Job / step | conclusion |
| ---------- | ---------- |
| Setup〜`Resolve job_run_id` | success（葉 `job_run_id` は UUID を生成） |
| `Run BATCH-016 live` | **failure** |
| `Run BATCH-017 Import Summary live` | skipped |

### 6.3 失敗内容（secretなし）

- **事実:** Environment `stg` と `DATABASE_URL`（`STG_DATABASE_URL`）は job に渡っている
- **事実:** live step（`--scaffold-demo` なし）まで到達している
- **事実:** DB接続で `psycopg.OperationalError` / `DatabaseError`。Supabase pooler への接続時に tenant/user が見つからない（`ENOTFOUND`）
- **推論:** workflow YAML の live化差分そのものより、Environment `stg` の `STG_DATABASE_URL`（または参照先DBテナント）が無効・陳腐化している可能性が高い
- **補足:** required reviewers 解除後のため、dispatch直後に job が開始された（承認待ちなし）

secret / 接続文字列 / プロジェクト参照の実値は本docsに記載しない。

### 6.4 代替確認（成功）

- 対象workflowのYAML構文確認
- 対象6葉の `environment: stg` / `STG_DATABASE_URL` / UUID生成の静的確認
- 対象6葉に `--scaffold-demo` が残っていないことの確認
- meaning複合とretry複合がlive葉へ共有pipeline IDを渡さないことの確認
- 既live BATCH-005〜008 / 017に差分がないことの確認

### 6.5 残リスク / 次アクション

| 優先 | 内容 | 担当 |
| ---- | ---- | ---- |
| high | Environment `stg` の `STG_DATABASE_URL` 妥当性確認・更新（secret実値はチャットに出さない） | Human |
| medium | Secret修正後、同一 ref で meaning複合（`max_items=1`）と distribution-metrics を再dispatch | AI / Human |
| low | 再dispatch成功後、本節の判定を FAIL→SUCCESS へ更新 | AI |

本Taskのworkflow差分（scaffold解除・stg配線・UUID分離）は静的確認と「live step到達」まで確認済み。
実DB書込成功の最終確認は、Secret修正後の再検証に委ねる。

## 7. 段階完了状況

| Phase | 状態 | 結果 |
| ----- | ---- | ---- |
| A | 完了 | scaffold / Environment / Run ID差分を確認 |
| B | 完了 | 対象6葉をstg live化 |
| C | 完了 | meaning / retry複合のRun IDを整合 |
| D | 完了 | 005〜008 / 017に意図しない差分なし |
| E | 実施済・FAIL | dispatch実施。run URL/conclusion記録。DB接続で失敗 |

## 8. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-30 | 初版。Phase A〜D完了、Phase EはHuman判断待ち |
| 2026-07-30 | Phase E実施。Human承認後にdispatch。DB接続失敗を記録 |
