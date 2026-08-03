# ジャンル地図キャンペーン BFS 段階同期手順

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連Issue | #1833（親Epic #1827） |
| 前提Decision | [ジャンル地図キャンペーン運用枠](../../../ai-logs/human-decisions/2026-08-03-batch-genre-map-campaign-ops-plan.md)（`decided` / #1829 / PR #1830） |
| 棚卸し | [external_genre 棚卸し](./ジャンル地図キャンペーン_external_genre棚卸し.md)（#1831 / PR #1832。未merge時は PR 側参照） |
| BATCH-001 | [BATCH-001 楽天ジャンル同期バッチ仕様書](../../06_実装設計/batch/BATCH-001_楽天ジャンル同期バッチ仕様書.md) |
| ラッパ | `scripts/batch/genre_map_campaign_runner.sh` |
| MVP fetch_plan | `100000` / `100003` / `100004` / `100005`（**置き換えない**） |

本手順は **ジャンル地図把握の別枠キャンペーン**専用である。
`local_daily_orchestrator.sh` / `local_weekly_orchestrator.sh` 全体は使わない。定常crontab（#1811 / #1818）は変更しない。
AI Agent は `--live-rakuten` を実行しない。live は Human のみ。

secret・token・APIキー・接続文字列・`.env` 実値は docs / Issue / PR / ログに含めない。

---

## 2. 目的

root `0` 起点の BFS で `external_genre` を全階層取り切りつつ、Decision の 1 Run 上限・QPS・soft/hard 容量ゲート・Slack 通知を守る。

---

## 3. BFS 運用（Decision 採択）

```text
1. キューを [0] で開始
2. キュー先頭から最大 20 ID を --genre-ids に載せて BATCH-001 を 1 Run
3. 各起点について「本体＋直下 children」が DB に入る
4. 新しく見えた非leaf（未展開）をキュー末尾へ追加
5. キュー空（全階層取り切り）または停止条件まで繰り返す
```

| 項目 | 値 |
| ---- | ---- |
| 起点 | root `0` |
| 深さ上限 | **なし**（full tree） |
| 1 Run `--genre-ids` 上限 | **20** |
| campaign QPS | **`max_qps=1`**（`RAKUTEN_MAX_QPS=1`） |
| 常用QPS=2 | 変更しない（キャンペーンのみ安全側 1） |
| 同時楽天 live | **常に1本**（商品収集 cron と重ねない） |

### 3.1 停止条件

追加のキャンペーン Run を止め、Human へ通知する（Slack 含む）。

1. 429 が連続（同一 Run で再発、またはクールダウン後も再発）
2. `paused` が増える
3. hard 上限到達（自動停止）
4. Human 中断
5. egress 不一致・secret 漏えい疑い・想定外の同時楽天 live

### 3.2 容量ゲート（初期値）

| ノブ | hard（自動停止） | soft（80%・Slack・継続可） |
| ---- | ---------------- | -------------------------- |
| `max_external_genre_rows` | 100,000 | 80,000 |
| `max_api_calls` | 100,000 | 80,000 |
| `max_runs` | 5,000 | 4,000 |
| `max_raw_storage_bytes` | 5 GiB | 4 GiB |
| `max_queue_size` | 50,000 | 40,000 |
| `max_depth` | なし | — |

---

## 4. 実行経路

| 経路 | 扱い |
| ---- | ---- |
| 本ラッパ → 葉 `python -m batch.application.genre_sync` | **推奨** |
| 葉 CLI を手で叩く | 可（上限・QPS・ゲートを手動遵守） |
| `local_weekly_orchestrator.sh` 全体 | **禁止** |
| `local_daily_orchestrator.sh` | **禁止** |
| Phase1/Phase2 crontab 変更 | **禁止** |
| GHA schedule / #1607 / GHA楽天 live | **対象外** |

---

## 5. ラッパ使い方

状態・ログは `scripts/batch/output-genre-map-campaign/`（gitignore 済み）に置く。

### 5.1 dry-run（AI / Human 共通・必須確認）

```bash
# リポジトリルートで
./scripts/batch/genre_map_campaign_runner.sh --dry-run --reset-state

# 複数チャンクのキュー消費プレビュー（DB があれば non-leaf enqueue も試す）
./scripts/batch/genre_map_campaign_runner.sh --dry-run --reset-state --max-runs-this-invocation 3
```

dry-run で見えるもの:

- キュー（初期 `[0]`）
- 次 Run の `--genre-ids`（≤20）
- soft/hard 現在値と level
- 葉 CLI コマンド例（**`--live-rakuten` なし**）
- Slack は env 未設定なら skip ログ。設定時は dry-run では送信せず要約のみ

### 5.2 live（Human のみ）

```bash
set -a && source .env && set +a   # 値はエコーしない
./scripts/batch/genre_map_campaign_runner.sh \
  --live-rakuten --i-am-human \
  --reset-state \
  --max-runs-this-invocation 1
```

| フラグ | 意味 |
| ------ | ---- |
| `--dry-run` | 計画のみ（既定パス） |
| `--live-rakuten` | 葉 CLI に live を付ける |
| `--i-am-human` | Human 明示。**無いと live 拒否**（AI 実行パスでは付けない） |
| `--reset-state` | キューを root `0` から初期化 |
| `--max-runs-this-invocation N` | この起動での Run 数上限 |
| `--seed-queue IDS` | 初期キュー上書き（通常不要） |
| `--skip-db-discover` | Run 後の DB non-leaf enqueue をスキップ |

live 時の葉呼び出し概要（ラッパが生成）:

```bash
cd apps/batch && RAKUTEN_MAX_QPS=1 uv run python -m batch.application.genre_sync \
  --job-run-id <uuid> --genre-ids <最大20個> --live-rakuten
```

`genre_sync` に `--max-qps` CLI が無いため、キャンペーン QPS は **`RAKUTEN_MAX_QPS=1`** で渡す。

**live 失敗時の状態:** 葉 CLI が非0のとき、当該チャンクはキューから消費しない（失敗前に take しない）。Slack 通知（env 設定時）と明示ログのあと非0で停止する。再開時は同じ先頭チャンクから再試行できる。

**root `0` のジャンル名:** 楽天 API は root の `nameJa` / `genreName` を空にすることがある。BATCH-001 adapt は root に限り `genre_name='root'` へフォールバックする（#1835）。非 root の名称欠落は従来どおり `GRS-EXT-103`。

**DB からの候補追加:** Run 成功後、`is_leaf = false` の既知ジャンルをキュー候補化し、`seen` / `queue` / `expanded` で重複排除する（親子リンク限定の SQL ではない）。

### 5.3 Slack フック

| env | 用途 |
| --- | ---- |
| `SLACK_BOT_TOKEN` | Slack API token（値をログに出さない） |
| `SLACK_CAMPAIGN_CHANNEL` または `SLACK_OPS_CHANNEL` | 投稿先 channel ID |

未設定時は通知を skip し、要約のみログする（失敗でキャンペーンを落とさない）。
実装は既存 `.github/scripts/slack-notify.cjs` の `postSlackMessage` を再利用する。

---

## 6. 葉 CLI 単独例（ラッパなし）

Human がラッパを使わず 1 Run だけ叩く場合の正本例。

```bash
set -a && source .env && set +a
cd apps/batch
JOB="$(uuidgen | tr '[:upper:]' '[:lower:]')"
RAKUTEN_MAX_QPS=1 uv run python -m batch.application.genre_sync \
  --job-run-id "$JOB" \
  --genre-ids 0 \
  --live-rakuten
```

- `--genre-ids` は **最大 20** 個まで。
- 次 Run の ID は、DB の non-leaf かつ未展開をキュー化し、先頭から最大 20 を載せる（§3）。
- AI はこのコマンドを live 実行しない。

---

## 7. 定常cron・#1811/#1818 との非干渉

| 注意 | 内容 |
| ---- | ---- |
| 時間分離 | 商品収集の楽天 live とキャンペーン live を同時にしない |
| 親シェル | weekly/daily 親をキャンペーン経路に含めない |
| crontab | #1811 / #1818 の行を変更・完了操作しない |
| MVP 4ID | fetch_plan 承認済み 4ID をキャンペーンで置き換えない |

---

## 8. AI / Human 境界

| 主体 | 可 | 不可 |
| ---- | -- | ---- |
| AI | dry-run、手順 docs、Decision 同期、棚卸し読取 | `--live-rakuten`、`--i-am-human` を付けた live、crontab/GHA schedule 変更 |
| Human | dry-run 確認後の live、停止判断、閾値調整 | secret を docs/PR に書くこと |

---

## 9. 確認チェックリスト

- [ ] dry-run でキュー・チャンク（≤20）・ゲートが見える
- [ ] 葉コマンドに親シェルが含まれない
- [ ] AI 実行ログに `--live-rakuten` が無い
- [ ] soft で Slack（または skip ログ）、hard で停止
- [ ] live 葉失敗時はキュー未消費のまま停止し、再開できる
- [ ] secret 実値がログ・docs に出ていない
- [ ] MVP 4ID を置き換えていない

---

## 10. 参照

- `ai-logs/human-decisions/2026-08-03-batch-genre-map-campaign-ops-plan.md`
- `scripts/batch/README.md`
- `scripts/batch/genre_map_campaign_runner.sh`
- `scripts/batch/lib/genre_map_campaign_common.sh`
- Issue #1833 / Epic #1827 / Related #1829 #1831 / 非変更 #1811 #1818
