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

| 項目 | 結果 |
| ---- | ---- |
| Run URL | 未実施のためなし |
| status | `not_run` |
| conclusion | `not_run` |
| 予定入力 | meaning複合 `max_items=1` |

### 6.1 未実施理由

Task DefinitionがPhase E前のHuman判断として、次を要求しているため停止した。

1. stg実データへの破壊的書込を許容するか
2. 低件数検証の `max_items` を `1` としてよいか
3. GitHub Environment `stg` のrequired reviewersによる承認負荷を許容するか
4. BATCH-016末尾でBATCH-017を続行する既存接続方針を維持してよいか

### 6.2 代替確認

- 対象workflowのYAML構文確認
- 対象6葉の `environment: stg` / `STG_DATABASE_URL` / UUID生成の静的確認
- 対象6葉に `--scaffold-demo` が残っていないことの確認
- meaning複合とretry複合がlive葉へ共有pipeline IDを渡さないことの確認
- 既live BATCH-005〜008 / 017に差分がないことの確認

### 6.3 残リスク

stg手動検証を実施するまで、実DB上の対象選定、書込結果、各jobのconclusion、
Environment承認フローは未確認である。

## 7. 段階完了状況

| Phase | 状態 | 結果 |
| ----- | ---- | ---- |
| A | 完了 | scaffold / Environment / Run ID差分を確認 |
| B | 完了 | 対象6葉をstg live化 |
| C | 完了 | meaning / retry複合のRun IDを整合 |
| D | 完了 | 005〜008 / 017に意図しない差分なし |
| E | Human判断待ち | stg dispatch未実施 |
