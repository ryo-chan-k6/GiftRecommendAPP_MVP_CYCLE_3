# ジャンル地図キャンペーン live 実行結果（完了）

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連Issue | #1841（親Epic #1827） |
| 前提Decision | [ジャンル地図キャンペーン運用枠](../../../ai-logs/human-decisions/2026-08-03-batch-genre-map-campaign-ops-plan.md)（`decided`） |
| 途中時点 | [live実行結果_途中](./ジャンル地図キャンペーン_live実行結果_途中.md)（#1839 / #1840） |
| 棚卸し（着手前） | [external_genre 棚卸し](./ジャンル地図キャンペーン_external_genre棚卸し.md)（#1831・15件） |
| BFS手順 | [BFS段階同期手順](./ジャンル地図キャンペーン_BFS段階同期手順.md) |
| ラッパ | `scripts/batch/genre_map_campaign_runner.sh` |
| 完了スナップショット | campaign-state `updated_at` **2026-08-03T11:27:42Z** / 記録日 2026-08-03 |
| 実測環境 | local Docker PostgreSQL（`supabase_db_gift-reco-local`） |
| 実行主体 | **Human live**（`--live-rakuten --i-am-human`）。AI は本 docs 同期のみ |
| 状態 | **完了（全階層取り切り）**。`queue` 空。`hard_stopped=false` |

secret・token・APIキー・接続文字列・`.env` 実値は本ドキュメントに含めない。

---

## 2. 目的

キャンペーン完了時点の件数・階層分布・Run 数を正本化し、Epic 完了判断と後続 BATCH-002/003 計画の参照土台にする。

---

## 3. 件数サマリ（事実）

### 3.1 external_genre 推移

| 時点 | 総件数 | 備考 |
| ---- | ------ | ---- |
| 着手前棚卸し（#1831） | **15** | root 未登録 |
| 途中（#1839） | **2,286** | level0–3。queue 残 |
| **完了（本記録）** | **16,537** | level0–5。queue=0 |

### 3.2 level 分布（完了）

| genre_level | 件数 |
| ----------- | ---- |
| 0 | 1 |
| 1 | 39 |
| 2 | 555 |
| 3 | 3,872 |
| 4 | 7,314 |
| 5 | 4,756 |
| **合計** | **16,537** |

| 指標 | 値 |
| ---- | -- |
| max `genre_level` | **5**（テーブル CHECK 上限と一致） |
| root `0` | 登録済み（`genre_name=root`） |
| MVP 4ID | **すべて present**（置き換えなし） |
| `is_leaf=false` | 2,002 |
| `is_leaf=true` | 14,535 |

> 注: BATCH-001 は直下 children を `is_leaf=true` 固定で upsert する。取り切り判定の正本は **campaign `queue` 空**（親子リンク discover、#1837）。

### 3.3 campaign-state（完了）

| 項目 | 値 |
| ---- | -- |
| `runs_completed`（累計） | **828** |
| うち連続自動実行 | **816**（途中時点 runs=12 のあと。828−12） |
| `api_calls_estimated` | **16,537**（expanded 件数と一致） |
| `expanded` | **16,537** |
| `queue` | **0** |
| `hard_stopped` | false |
| 終了条件 | ログ `queue empty — campaign complete` |

---

## 4. 完了判定

| 観点 | 結果 |
| ---- | ---- |
| Decision「全階層取り切り（キュー空）」 | **達成** |
| hard 自動停止 | **未到達**（余裕あり。rows 16,537 ≪ hard 100,000） |
| soft 80% rows | 未到達（soft 80,000） |
| MVP 4ID | 維持 |
| 定常crontab変更 | なし（本キャンペーン範囲） |
| AI live | なし |

---

## 5. ブロッカー解消の要約（完了までに実施済み）

| 課題 | 対応 | Issue/PR |
| ---- | ---- | -------- |
| root `0` 名称欠落 `GRS-EXT-103` | adapt root フォールバック | #1835 / #1836 |
| discover が `is_leaf` 依存で queue 空 | 親子リンク discover + enqueue 修正 | #1837 / #1838 |
| 途中記録 | collect-docs 途中 | #1839 / #1840 |

---

## 6. 後続 BATCH-002/003 向け参照メモ

| 項目 | 内容 |
| ---- | ---- |
| 地図 | local `external_genre` に楽天ジャンル **16,537** 行（level0–5）が揃った |
| MVP 4ID | 商品収集の承認済み起点は **変更しない** |
| 利用（推論） | level・親リンク・leaf を集計し、BATCH-002/003 の対象ジャンル選定・Run分割の入力にする。拡大実行そのものは別 Task / Decision |
| 再同期 | 地図の差分更新が必要ならキャンペーン枠を再適用（定常 cron に混ぜない） |

---

## 7. Human 判断依頼

| 判断 | 内容 |
| ---- | ---- |
| Epic #1827 | 本完了結果をもって成果物完了とし、develop 向け Epic PR へ進むか |
| BATCH-002/003 | 地図を使った取得計画の別 Task 化タイミング |
| 途中 docs | 履歴として残す（本完了 docs を正とする） |

---

## 8. 関連

| ドキュメント | 関係 |
| ------------ | ---- |
| [live実行結果_途中](./ジャンル地図キャンペーン_live実行結果_途中.md) | 途中スナップショット（履歴） |
| [楽天Fetch運用方針](./楽天Fetch運用方針.md) §11.5 | キャンペーン枠・本完了へのリンク |
| [BFS段階同期手順](./ジャンル地図キャンペーン_BFS段階同期手順.md) | 実行手順 |
| [棚卸し](./ジャンル地図キャンペーン_external_genre棚卸し.md) | 着手前ベースライン |
