# fetch_plan 拡大 第1波・1ジャンル手動実行手順

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | 運用手順正本（第1波 fetch_plan 反映・手動1ジャンル起動） |
| 作成日 | 2026-08-04 |
| 関連Issue | [#1846](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1846)（本手順） / 親Epic [#1843](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1843) |
| 前提Decision | [BATCH-002/003 拡大候補](../../../ai-logs/human-decisions/2026-08-04-batch-fetch-plan-expansion-candidates.md)（`decided` / #1844 / PR #1845） |
| 運用方針 | [楽天Fetch運用方針](./楽天Fetch運用方針.md) §10 No.12 / §11.6 / §5.3.4 |
| 親シェル設計 | [local薄いオーケストレータ設計・運用手順](./local薄いオーケストレータ設計・運用手順.md) |
| 定常cron正本 | [local_cron_Phase1_crontab運用手順](./local_cron_Phase1_crontab運用手順.md)（**本手順では変更しない**） |
| 状態 | 手順正本化済み。**live 起動判断・実行は Human**。AI は `--live-rakuten` しない |

secret・token・APIキー・egress IP・接続文字列・`.env` 実値は記載しない。

---

## 2. 目的と非目的

### 2.1 目的

- 案B（第1波追加6ID）と **1ジャンル単位実行** を、Human が安全に起動できる CLI / 切替ゲート付き手順として正本化する
- BATCH-003 優先・BATCH-002 は smoke 後必要最小（`max_pages=1`）の順序を明記する
- 後続 Task（`staged-collect-wave1` / #1847）の着手ゲートを明示する

### 2.2 非目的（out of scope）

| 対象 | 扱い |
| ---- | ---- |
| 拡大 live 収集の実行本体・結果記録 | 後続 `staged-collect-wave1`（#1847）・Human |
| 定常crontab変更 | **禁止**（#1811 / #1818。別Task・Human承認） |
| `local_daily_orchestrator.sh` / `local_weekly_orchestrator.sh` の無断変更 | **禁止** |
| AI による `--live-rakuten` | **禁止** |
| GHA楽天live / #1607 / `on.schedule` | 対象外維持 |
| MVP 4ID の置き換え | **禁止**（追加のみ） |
| 子・孫ジャンル自動展開 | **導入しない**（明示指定 ID のみ） |
| keyword route 本格常用化 | 本手順外 |
| secret 実値の表示・変更 | **禁止** |

---

## 3. 承認スコープと実行単位（採択）

正本は [拡大候補 Decision Log](../../../ai-logs/human-decisions/2026-08-04-batch-fetch-plan-expansion-candidates.md)。本節は運用向け要約。

### 3.1 MVP 維持（置き換え禁止）

```text
100000 / 100003 / 100004 / 100005
```

Phase1 定常cron のジャンルローテは上記のまま。本手順で crontab 行を案Bへ差し替えない。

### 3.2 第1波追加（案B・承認スコープ）

| external_genre_id | genre_name |
| ----------------: | ---------- |
| 101381 | カタログギフト・チケット |
| 551167 | スイーツ・お菓子 |
| 510901 | 日本酒・焼酎 |
| 216129 | ジュエリー・アクセサリー |
| 558944 | キッチン用品・食器・調理器具 |
| 100939 | 美容・コスメ・香水 |

```text
承認スコープ合計（MVP + 案B）: 10 ID
実行単位: 常に --genre-ids 1本（案B 6本を同時・並列しない）
```

### 3.3 実行方針

| 項目 | 決定 |
| ---- | ---- |
| 承認スコープと実行 | **分離**。スコープに載っていても一度に全部は回さない |
| `--genre-ids` | **常に1本** |
| 同時楽天 live | **禁止**（既存どおり横断1本） |
| Ranking | `--ranking-genre-ids 100005` を維持（#1765。新IDを Ranking に載せない） |
| BATCH 優先 | **BATCH-003 優先**。BATCH-002 は 003 smoke 後に新IDを `max_pages=1` で必要最小 |
| 明示指定 | BATCH-003 genre は fetch_plan / CLI で明示した ID のみ。地図の子・孫を自動展開しない |
| 1 Run 予算 | 運用方針 §5.3.4 維持。新ID初回は低値 smoke 推奨 |
| カタログ深さ | 打ち切りなし（`exhausted` まで）。1 Run / 1日で取り切らない想定 |
| ジャンル切替 | Human が容量・429・Run失敗を確認してから次IDへ |

---

## 4. 起動経路

| 経路 | 扱い |
| ---- | ---- |
| `local_daily_orchestrator.sh`（001スキップ・cursor 既存時） | **推奨**（日次相当・003起点） |
| `local_weekly_orchestrator.sh`（001→002→003…） | 新IDでジャンル同期が必要な場合に Human 判断で使用可。**案Bを crontab に載せない** |
| 葉 Batch を個別 cron に載せる | **禁止** |
| Phase1 / Phase2 定常crontab の書き換え | **禁止**（本手順外） |
| GHA 楽天 live | **禁止** |

親シェルの CLI 表・flock・失敗停止は [local薄いオーケストレータ設計・運用手順](./local薄いオーケストレータ設計・運用手順.md) を正とする。本手順は **手動1ジャンル起動の運用境界**を追加する。

---

## 5. Human 手動起動手順（最初の1ID）

### 5.1 起動前チェック

| No | 確認 |
| --: | ---- |
| 1 | 拡大候補 Decision が `decided`（案B・1ジャンル単位）である |
| 2 | ジャンル地図キャンペーンが完了し、対象 ID が `external_genre` に存在する（情報源。自動展開はしない） |
| 3 | 他の楽天 live（定常cron・地図キャンペーン・別手動）が動いていない |
| 4 | 登録済み egress の **local / WSL** で実行する（GHA 禁止） |
| 5 | secret は `.env` 等から読む。値をエコー・docs・Issue・PR に出さない |
| 6 | 最初の1IDは推奨 **`101381`**（カタログギフト・チケット）。変更する場合は Human 明示判断 |

### 5.2 dry-run（AI 可・推奨）

live 前に順序・flock・Run ID だけ確認する（楽天 HTTP なし）。

```bash
# リポジトリルート。--genre-ids は常に1本
./scripts/batch/local_daily_orchestrator.sh --dry-run \
  --genre-ids 101381 --ranking-genre-ids 100005 \
  --pages-per-run=1 --max-qps 1
```

### 5.3 初回 smoke live（Human のみ・低値）

運用方針 §5.3.4 の smoke（`pages_per_run=1`）相当。`--live-rakuten` は Human 専用。

```bash
set -a && source .env && set +a

# 【Human】第1波最初の1ID・smoke（例: 101381）
# Ranking は 100005 のまま。案Bを複数並べない
./scripts/batch/local_daily_orchestrator.sh --live-rakuten \
  --genre-ids 101381 --ranking-genre-ids 100005 \
  --pages-per-run=1 --max-qps 1
```

確認観点（secret なし）:

- exit 成功 / 失敗理由（429・egress・cursor）
- BATCH-003 が当該ジャンルで進行したか
- DB / Raw の異常増分がないか

### 5.4 初期 live → 通常継続（Human）

smoke 問題なし後:

| 段階 | `--pages-per-run` | 備考 |
| ---- | ----------------: | ---- |
| 初期 live（最初の数 Run） | 10 | §5.3.4 初期live |
| 通常継続 | 60 | Phase1 定常と同値。安定後 |
| 加速 | 使わない | 第1波では加速ノブ不使用を推奨 |

```bash
# 【Human】初期 live 例（同一ジャンルを継続。切替は §6）
./scripts/batch/local_daily_orchestrator.sh --live-rakuten \
  --genre-ids 101381 --ranking-genre-ids 100005 \
  --pages-per-run=10 --max-qps 1

# 【Human】通常継続例
./scripts/batch/local_daily_orchestrator.sh --live-rakuten \
  --genre-ids 101381 --ranking-genre-ids 100005 \
  --pages-per-run=60 --max-qps 1
```

### 5.5 BATCH-002（必要最小・smoke 後）

BATCH-003 smoke 成功後、新IDの Ranking が必要なら **別 Run** で必要最小のみ。親シェル既定の Ranking は `100005` のため、新IDを Ranking に載せる場合は葉 BATCH-002 / 明示フラグの扱いを仕様書に従い、**`max_pages=1`** 相当に抑える。

| 項目 | 扱い |
| ---- | ---- |
| 優先 | **003 が先**。002 と同時に新IDを広げない |
| 予算 | `max_pages=1`（運用方針 §11.6 / Decision） |
| Ranking 非対応 | #1765 どおり。新IDが Ranking 400 の場合は無理に載せない |

---

## 6. ジャンル切替ゲート

次の案B ID（例: `551167`）へ進む前に、Human が以下を確認する。**未確認のまま次IDを起動しない。**

| No | ゲート | 不合格時 |
| --: | ------ | -------- |
| 1 | 直近 Run が致命失敗していない | 原因確認・クールダウン（運用方針 §5.3.5 / §10） |
| 2 | 429 / `rate_limited` の再発がない | QPS=1 維持・`pages_per_run` 半減・15分以上待機 |
| 3 | DB / Raw 容量に余裕がある（運用方針 §5.3.5） | 切替延期・ノブ縮小 |
| 4 | 他の楽天 live が動いていない | 終了待ち |
| 5 | 次IDが承認スコープ（案B）内である | 案B外は第2波別Decision |

切替後も `--genre-ids` は **1本のみ**。例:

```bash
# 【Human】切替後の smoke（別ジャンル。並列しない）
./scripts/batch/local_daily_orchestrator.sh --live-rakuten \
  --genre-ids 551167 --ranking-genre-ids 100005 \
  --pages-per-run=1 --max-qps 1
```

---

## 7. 後続 staged-collect の着手ゲート

後続 Task Definition: `prompts/definitions/tasks/batch-fetch-plan-expand/staged-collect-wave1.yaml`（Issue #1847）。

| No | 条件 | 状態 |
| --: | ---- | ---- |
| 1 | 拡大候補 Decision が `decided` | **充足**（#1844） |
| 2 | 本手順（fetch-plan-apply）が正本化され、Human が最初の1IDを起動できる CLI 例がある | **本docsで充足** |
| 3 | 楽天Fetch運用方針 §11.6 が本手順へ接続されている | 本PRで同期 |
| 4 | 定常crontab・親シェル無断変更・AI live・GHA楽天liveを含まない | 本Taskで維持 |
| 5 | live 実行・結果docs同期 | **#1847 / Human**（本手順の範囲外） |

本手順の完了は **「起動できる状態」まで**。実際の `--live-rakuten` 起動判断・実行・結果記録は Human / 後続 Task。

---

## 8. 関連資料

| 資料 | 用途 |
| ---- | ---- |
| [BATCH-002/003 拡大候補 Decision](../../../ai-logs/human-decisions/2026-08-04-batch-fetch-plan-expansion-candidates.md) | 採択正本（案B・1ジャンル単位） |
| [楽天Fetch運用方針](./楽天Fetch運用方針.md) | §5.3 / §10 No.12 / §11.6 |
| [local薄いオーケストレータ設計・運用手順](./local薄いオーケストレータ設計・運用手順.md) | 親シェル CLI・排他 |
| [local_cron_Phase1_crontab運用手順](./local_cron_Phase1_crontab運用手順.md) | 定常cron（変更しない） |
| [BATCH-003仕様書](../../06_実装設計/batch/BATCH-003_楽天商品疑似差分取得バッチ仕様書.md) | 商品疑似差分 |
| [BATCH-002仕様書](../../06_実装設計/batch/BATCH-002_楽天ランキングスナップショット取得バッチ仕様書.md) | Ranking |
| [scripts/batch/README.md](../../../scripts/batch/README.md) | 起動例の入口 |
| [ジャンル地図キャンペーン_live実行結果_完了](./ジャンル地図キャンペーン_live実行結果_完了.md) | 地図完了前提 |

---

## 9. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-08-04 | 初版（#1846）。案B 6ID・1ジャンル単位・003優先・smoke/切替ゲート・staged-collect 着手条件を正本化 |
