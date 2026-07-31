# BATCH-015 Embedding live stg検証結果

## 1. 検証概要

| 項目 | 内容 |
| --- | --- |
| 対象Issue | `#1776` |
| 対象Branch | `feature/task-1776-embedding-live` |
| 対象commit | `732e9ad04c89ec655658d62b54260785562ce0d7` |
| 実施日 | 2026-07-31（JST） |
| 対象環境 | GitHub Environment `stg` |
| workflow | `.github/workflows/batch-item-embedding.yml` |
| Run | [30567182438](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30567182438) |
| conclusion | `success` |

本結果は、BATCH-015のstg DB経路と明示live Embedding経路を低件数で確認した記録である。production、schedule、Secret設定の作成・変更は行っていない。

## 2. 実行条件

| 入力・条件 | 設定 |
| --- | --- |
| trigger | `workflow_dispatch` |
| ref | `feature/task-1776-embedding-live` |
| `live_embedding` | `true` |
| `max_items` | `1` |
| `queue_batch_size` | `1` |
| `source` | 既定値 `rakuten` |
| `item_ids` / `queue_ids` | 未指定 |
| `job_run_id` | workflow内でUUIDを生成 |
| DB認証 | `STG_DATABASE_URL` Secretを`DATABASE_URL`として参照 |
| Embedding認証 | `OPENAI_API_KEY` Secretを参照 |

Secret値、DB URL、入力全文、Embedding vector全文は取得・表示・記録していない。

## 3. stg実行結果

GitHub Actionsの安全な件数要約は次のとおり。

```text
status=succeeded
db_reader=postgres
db_writer=postgres
embedding_backend=http
claimed=1
generated=1
skipped=0
failed=0
item_embedding_writes=1
```

確認できた事実:

- 対象Queueが1件存在し、追加の先行BATCH-014実行は不要だった
- `CurrentVersionResolver`で解決したcurrent Embedding model UUIDを利用して処理が完了した
- 実HTTP Embedding backendで1件生成し、`item_embedding`を1件書き込んだ
- `generate_embedding`後に既存`api_call_log` writer経路を通る実装であり、同経路を含むjobが成功した
- Queueは成功終端し、失敗・skipは0件だった
- API呼出を伴う再実行は行っていない

`api_call_log`行の直接SELECT確認は行っていない。DB行の追加確認が必要な場合も、Secretを表示せず、読み取り専用の別手順で確認する。

## 4. コスト目安

- 実API呼出は1件のみ
- Human確定の保守的な運用上限は`$0.01/run`
- 実際のtoken使用量・請求額は取得していないため、厳密な実績額は未確認
- 今回は1件・再実行なしであり、運用上のコスト目安は`$0.01未満/run`

## 5. local検証結果

| 検証 | 結果 |
| --- | --- |
| Embedding対象unit tests | `87 passed` |
| `apps/batch` unit tests全体 | `785 passed` |
| workflow / Task Definition / Review Definition YAML parse | `3 passed` |
| workflow静的検証 | unit test内でpass |
| Secret直書きパターン検査 | `PASS` |
| `git diff --check` | `PASS` |
| IDE lint | 新規errorなし |

`actionlint`はlocal環境に未導入だったため未実施。代替としてYAML parse、workflow静的unit test、実GitHub Actions run成功を確認した。

## 6. 安全性確認

- `live_embedding`は`workflow_dispatch` / `workflow_call`とも既定`false`
- `true`のときだけ`--live-embedding`を付与
- 既定`false`ではlive DB + scaffold Embedding clientとなり、実OpenAIを呼ばない
- workflowに`cron` / `schedule`を追加していない
- workflow権限は`contents: read`のみ
- `BATCH_EMBEDDING_LIVE` Variableの設定・変更は行っていない
- production、DDL、migration、OpenAPI、generated、`apps/web|api|reco`は変更していない
- meaning/retry複合workflowは、葉workflowの既定`false`で安全性を維持できるため変更していない

## 7. 残リスク・Human Review観点

- `api_call_log`の直接SELECTによる行確認は未実施
- 実請求額は未確認であり、`$0.01未満/run`は運用上の保守的な目安
- `astral-sh/setup-uv@v5`のNode.js 20非推奨warningがGitHub Actionsに出たが、本Taskの実行結果には影響しなかった
- Human Reviewでは、明示live限定、Secret参照、UUID伝播、既定scaffold、production / schedule非変更を重点確認する
