# ジャンル地図キャンペーン live 実行結果（途中時点）

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連Issue | #1839（親Epic #1827） |
| 前提Decision | [ジャンル地図キャンペーン運用枠](../../../ai-logs/human-decisions/2026-08-03-batch-genre-map-campaign-ops-plan.md)（`decided`） |
| 棚卸し（着手前） | [external_genre 棚卸し](./ジャンル地図キャンペーン_external_genre棚卸し.md)（#1831） |
| BFS手順 | [BFS段階同期手順](./ジャンル地図キャンペーン_BFS段階同期手順.md)（#1833 / #1837） |
| ラッパ | `scripts/batch/genre_map_campaign_runner.sh` |
| スナップショット時刻 | **2026-08-03T05:46:10Z**（campaign-state `updated_at`） / 記録日 2026-08-03 |
| 実測環境 | local Docker PostgreSQL（`supabase_db_gift-reco-local`） |
| 実行主体 | **Human live**（`--live-rakuten --i-am-human`）。AI は本 docs 同期のみ（live なし） |
| 状態 | **進行中（未完了）**だった途中記録。**完了後の正本は [live実行結果_完了](./ジャンル地図キャンペーン_live実行結果_完了.md)（#1841）** |

secret・token・APIキー・接続文字列・`.env` 実値は本ドキュメントに含めない。

---

## 2. 目的

途中時点の件数・階層分布・キャンペーン state・障害/修正履歴を正本化し、継続 live と後続 BATCH-002/003 計画の参照土台にする。

---

## 3. 件数サマリ（事実）

### 3.1 external_genre

| 時点 | 総件数 | 備考 |
| ---- | ------ | ---- |
| 着手前棚卸し（#1831） | **15** | root `0` 未登録。level1=2 / level2=13 |
| 本スナップショット | **2,286** | root 登録済み。level0〜3 まで到達 |

#### level 分布（本スナップショット）

| genre_level | 件数 |
| ----------- | ---- |
| 0 | 1 |
| 1 | 39 |
| 2 | 555 |
| 3 | 1,691 |
| **合計** | **2,286** |

#### その他

| 指標 | 値 |
| ---- | -- |
| root `0` | **登録済み**（`genre_name=root` フォールバック適用後） |
| MVP 4ID（100000/100003/100004/100005） | **すべて present**（置き換えなし） |
| `is_leaf=false` | 172 |
| `is_leaf=true` | 2,114 |
| `parent_external_genre_id` NULL | 40（root + 旧来の最上位相当を含む） |
| 親あり | 2,246 |

> 注: BATCH-001 は直下 children を常に `is_leaf=true` で upsert する。`is_leaf` は地図取り切り判定の正本ではない（discover は親子リンク、#1837）。

### 3.2 campaign-state（Epic worktree）

状態ファイル: `scripts/batch/output-genre-map-campaign/campaign-state.json`（gitignore。値はここに実体を貼らない）

| 項目 | 値 |
| ---- | -- |
| `runs_completed` | **12** |
| `api_calls_estimated` | **221**（1 Run の genre-id 数の累計推定） |
| `expanded` 件数 | **221** |
| `queue` 件数 | **2,065** |
| `hard_stopped` | false |
| queue 先頭（参考） | `402486`, `402512`, `403678`, …（次チャンク最大20） |

### 3.3 api_call_log（genre_search・直近1日・集計のみ）

| call_status | error_code | count |
| ----------- | ---------- | ----- |
| succeeded | （なし） | 222 |
| failed | GRS-EXT-103 | 2 |

失敗2件は初期の root `0` 名称欠落（修正前）。成功後の本線 live では同エラーは再現していない（ログ・修正 #1836 と整合）。

---

## 4. タイムライン（要約・事実）

| 時刻（JST 目安） | 出来事 |
| ---------------- | ------ |
| 13:44–13:45 | root `0` live 失敗 ×2（`GRS-EXT-103` 名称欠落）。queue 未消費 |
| — | #1835 / PR #1836: root 名フォールバック修正 → Epic merge |
| 13:56 | root `0` live 成功（旧 discover では children enqueue されず queue 空） |
| — | #1837 / PR #1838: 親子リンク discover + enqueue 修正 → Epic merge |
| 14:08 | 起動時 discover で level1 **39** enqueue。以降 Human live 継続 |
| 14:08–14:46 | 複数 Run（state 上 `runs_completed=12`）。件数 15→2,286。queue 2,065 残 |
| （本記録） | **一時停止して collect-docs**（キャンペーン未完了） |

Run 単位の genre-ids 全列挙は campaign.log / state に残る。本 docs では件数・階層・進捗の要約を正本とする（secret なし）。

---

## 5. 修正・ブロッカー履歴（本キャンペーン内）

| 課題 | 対応 | Issue/PR |
| ---- | ---- | -------- |
| root `0` で `nameJa` 空 → `GRS-EXT-103` | adapt で root 限定 `genre_name='root'` | #1835 / #1836 |
| children が `is_leaf=true` 固定で queue が空 | discover を `parent∈expanded` へ。enqueue stdin バグも修正 | #1837 / #1838 |

---

## 6. 定常cron・境界の確認

| 項目 | 状態 |
| ---- | ---- |
| Phase1 crontab（#1811）変更 | **なし**（本キャンペーン差分に含まない） |
| Phase2 crontab（#1818）変更 | **なし** |
| `local_daily` / `local_weekly` 親シェル実行 | **未使用**（葉 BATCH-001 + キャンペーンラッパのみ） |
| GHA schedule / #1607 / GHA楽天live | **対象外のまま** |
| AI `--live-rakuten` | **なし**（Human のみ） |
| MVP fetch_plan 4ID | **置き換えなし** |

商品収集 cron（05:00 JST）との同時楽天 live は Decision どおり避けること。

---

## 7. 次Run候補

| 項目 | 内容 |
| ---- | ---- |
| 再開方法 | Epic worktree で `--reset-state` **なし**に live 継続 |
| 次チャンク | state の queue 先頭から最大 **20** ID |
| 残作業感（推論） | queue≈2,065・api_calls_est≈221。level3 まで到達済みで、さらに下層があれば enqueue が増える。取り切りまで **追加数十〜百超 Run** の可能性（未確認・QPS=1前提） |
| 停止条件 | Decision: 429連続 / paused増 / hard / Human中断 / egress不一致等 |

```bash
# Human live 継続例（AI は実行しない）
./scripts/batch/genre_map_campaign_runner.sh \
  --live-rakuten --i-am-human \
  --max-runs-this-invocation 1
```

---

## 8. 後続 BATCH-002/003 向け参照メモ

| 項目 | 内容 |
| ---- | ---- |
| 地図の用途 | ジャンル全体の ID・階層把握。商品収集の大規模拡大そのものは本キャンペーン外 |
| MVP 4ID | `100000` / `100003` / `100004` / `100005` は **維持**（Decision 2026-07-31） |
| 現状の地図粒度 | level1 全39は取得済み。level2/3 は大幅増。**全階層取り切りは未了** |
| 計画への使い方（推論） | 完了後に level・leaf・親リンクを集計し、BATCH-002/003 の対象ジャンル選定の入力にする。途中時点でも level1 一覧は参照可能 |

---

## 9. Human 判断依頼

| 判断 | 選択肢（例） |
| ---- | ------------ |
| キャンペーン継続 | そのまま live 継続 / 件数上限で一時停止 / 完了扱い（非推奨: queue 残） |
| 本スナップショット | 途中記録として採用（本 PR）し、完了時に追記または別 docs |
| BATCH-002/003 反映 | 取り切り後に計画 Task 化 / 途中の level1 だけで暫定検討 |

---

## 10. 再測クエリ（secretなし）

```bash
docker exec supabase_db_gift-reco-local psql -U postgres -d postgres -c \
  "SELECT count(*) AS rows FROM external_genre;"
docker exec supabase_db_gift-reco-local psql -U postgres -d postgres -c \
  "SELECT genre_level, count(*) FROM external_genre GROUP BY 1 ORDER BY 1;"
```

state は worktree の `scripts/batch/output-genre-map-campaign/campaign-state.json` を参照（docs に全文を貼らない）。

---

## 11. 関連

| ドキュメント | 関係 |
| ------------ | ---- |
| [live実行結果_完了](./ジャンル地図キャンペーン_live実行結果_完了.md) | **完了後の正本**（#1841）。本 docs は途中履歴 |
| [楽天Fetch運用方針](./楽天Fetch運用方針.md) §11.5 | キャンペーン枠・本結果へのリンク |
| [BFS段階同期手順](./ジャンル地図キャンペーン_BFS段階同期手順.md) | 実行手順正本 |
| [棚卸し](./ジャンル地図キャンペーン_external_genre棚卸し.md) | 着手前ベースライン |
