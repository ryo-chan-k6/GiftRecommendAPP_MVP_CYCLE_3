# ジャンル地図キャンペーン external_genre 棚卸し

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連Issue | #1831（親Epic #1827） |
| 前提Decision | [ジャンル地図キャンペーン運用枠](../../../ai-logs/human-decisions/2026-08-03-batch-genre-map-campaign-ops-plan.md)（`decided` / #1829 / PR #1830） |
| MVP fetch_plan | [2026-07-31](../../../ai-logs/human-decisions/2026-07-31-rakuten-fetch-mvp-fetch-plan.md)（`100000` / `100003` / `100004` / `100005`。**置き換えない**） |
| テーブル定義 | [external_genre テーブル定義書](../../06_実装設計/database/external_genre_テーブル定義書.md) |
| BATCH-001 | [BATCH-001 楽天ジャンル同期バッチ仕様書](../../06_実装設計/batch/BATCH-001_楽天ジャンル同期バッチ仕様書.md) |
| 記録日 | 2026-08-03 |
| 実測環境 | local Docker PostgreSQL（コンテナ名 `supabase_db_gift-reco-local`） |
| 実行境界 | **読取のみ**。`--live-rakuten`・定常crontab変更・親オーケストレータ実行は含まない |

secret・token・APIキー・接続文字列・`DATABASE_URL` 実値は本ドキュメントに含めない。

---

## 2. 目的

キャンペーン着手前の現状把握として、`external_genre` の件数・`genre_level` 分布・leaf/親・MVP 4ID 有無を正本化し、後続 runner（root `0` BFS）の起点把握に使う。

---

## 3. 棚卸し手順（再測用）

### 3.1 前提

| 項目 | 内容 |
| ---- | ---- |
| 対象DB | local Supabase DB コンテナ（例: `supabase_db_gift-reco-local`） |
| 接続 | `docker exec … psql`。接続文字列実値は docs / Issue / PR / ログに書かない |
| 権限 | SELECT のみ。INSERT / UPDATE / DELETE / DDL は行わない |
| AI境界 | AI は手順・結果docs同期可。live 楽天同期は Human |

### 3.2 集計クエリ方針（secretなし）

以下を `psql -c` で実行する（heredoc を `docker exec` に直接渡すと欠落することがあるため `-c` 推奨）。

```bash
DB=supabase_db_gift-reco-local
run() { docker exec "$DB" psql -U postgres -d postgres -c "$1"; }

# 件数
run "SELECT COUNT(*) AS total_rows FROM external_genre;"

# source 分布
run "SELECT source, COUNT(*) AS cnt FROM external_genre GROUP BY source ORDER BY source;"

# level 分布
run "SELECT genre_level, COUNT(*) AS cnt FROM external_genre GROUP BY genre_level ORDER BY genre_level;"

# leaf 分布
run "SELECT is_leaf, COUNT(*) AS cnt FROM external_genre GROUP BY is_leaf ORDER BY is_leaf;"

# level × leaf
run "SELECT genre_level, is_leaf, COUNT(*) AS cnt FROM external_genre GROUP BY genre_level, is_leaf ORDER BY genre_level, is_leaf;"

# 親ごとの子件数
run "SELECT parent_external_genre_id, COUNT(*) AS child_cnt FROM external_genre GROUP BY parent_external_genre_id ORDER BY child_cnt DESC, parent_external_genre_id NULLS FIRST;"

# 全行概要（ID・名称・親・level・leaf・fetched_at）
run "SELECT external_genre_id, genre_name, parent_external_genre_id, genre_level, is_leaf, fetched_at FROM external_genre ORDER BY genre_level, external_genre_id;"

# root 0 の有無
run "SELECT external_genre_id, genre_name, parent_external_genre_id, genre_level, is_leaf FROM external_genre WHERE external_genre_id = 0;"

# MVP 4ID 有無
run "SELECT g.external_genre_id, CASE WHEN e.external_genre_id IS NULL THEN 'missing' ELSE 'present' END AS status, e.genre_name, e.genre_level, e.is_leaf, e.parent_external_genre_id FROM (VALUES (100000::bigint),(100003),(100004),(100005)) AS g(external_genre_id) LEFT JOIN external_genre e ON e.external_genre_id = g.external_genre_id ORDER BY g.external_genre_id;"

# テーブルサイズ（容量ゲート参照用・実値パスなし）
run "SELECT pg_size_pretty(pg_total_relation_size('external_genre')) AS total_relation_size, pg_size_pretty(pg_relation_size('external_genre')) AS table_size, pg_size_pretty(pg_indexes_size('external_genre')) AS indexes_size;"
run "SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size;"
```

### 3.3 容量確認コマンド（Decision §2.3 参照）

Decision の容量ゲート（soft/hard）は runner が自動計測する前提だが、棚卸し時点の目安として次を記録してよい（値の解釈のみ。接続情報は出さない）。

```bash
# ホスト空き（マウント点は環境依存。例は / ）
df -h /

# DB / テーブルサイズは §3.2 の pg_size_pretty 系
```

| ノブ（Decision） | hard | soft | 本棚卸しでの参照 |
| ---- | ---- | ---- | ---- |
| `max_external_genre_rows` | 100,000 | 80,000 | 現状件数と比較 |
| `max_raw_storage_bytes` | 5 GiB | 4 GiB | `external_genre` / DB サイズと比較 |

---

## 4. 実測結果（2026-08-03）

| 項目 | 値 |
| ---- | ---- |
| 実測日時 | 2026-08-03（JST） |
| 実行者 | AI Agent（local Docker 読取。secret非表示） |
| 総件数 | **15** |
| source | `rakuten` のみ（15） |
| root `0` | **未登録**（0件） |
| non-leaf | 2 |
| leaf | 13 |
| `external_genre` total_relation_size | 80 kB（table 8 kB / indexes 64 kB） |
| DB size（`current_database`） | 27 MB |
| ホスト空き（`df -h /`） | Size 1007G / Used 22G / Avail 935G / Use% 3% |

### 4.1 genre_level 分布

| genre_level | 件数 |
| ----------: | ---: |
| 1 | 2 |
| 2 | 13 |
| 合計 | 15 |

### 4.2 is_leaf 分布 / level×leaf

| genre_level | is_leaf | 件数 |
| ----------: | ------- | ---: |
| 1 | false | 2 |
| 2 | true | 13 |

### 4.3 親（parent）分布

| parent_external_genre_id | 子件数 | 備考 |
| -----------------------: | -----: | ---- |
| （NULL） | 2 | level 1 の `100000` / `100005`（root 0 未登録のため親なし） |
| 100000 | 6 | |
| 100005 | 7 | |

### 4.4 全行一覧

| external_genre_id | genre_name | parent | genre_level | is_leaf | fetched_at（UTC） |
| ----------------: | ---------- | -----: | ----------: | ------- | ----------------- |
| 100000 | 百貨店・総合通販・ギフト | NULL | 1 | false | 2026-08-01 08:19:48 |
| 100005 | 花・ガーデン・DIY | NULL | 1 | false | 2026-08-02 20:00:03 |
| 100001 | 百貨店 | 100000 | 2 | true | 2026-08-01 08:19:48 |
| 100002 | 総合通販・ディスカウント | 100000 | 2 | true | 2026-08-01 08:19:48 |
| 100003 | 贈答品・ギフト | 100000 | 2 | true | 2026-08-01 08:19:48 |
| 100004 | 輸入雑貨 | 100000 | 2 | true | 2026-08-01 08:19:48 |
| 101736 | その他 | 100000 | 2 | true | 2026-08-01 08:19:48 |
| 101972 | スーパー | 100000 | 2 | true | 2026-08-01 08:19:48 |
| 100012 | ガーデニング・農業 | 100005 | 2 | true | 2026-08-02 20:00:03 |
| 100880 | エクステリア・ガーデンファニチャー | 100005 | 2 | true | 2026-08-02 20:00:03 |
| 100890 | DIY・工具 | 100005 | 2 | true | 2026-08-02 20:00:03 |
| 100893 | 木材・建築資材・設備 | 100005 | 2 | true | 2026-08-02 20:00:03 |
| 101737 | その他 | 100005 | 2 | true | 2026-08-02 20:00:03 |
| 113084 | 花・観葉植物 | 100005 | 2 | true | 2026-08-02 20:00:03 |
| 567273 | 研究・実験用品 | 100005 | 2 | true | 2026-08-02 20:00:03 |

### 4.5 MVP fetch_plan 4ID

| external_genre_id | status | genre_level | is_leaf | 置き換え |
| ----------------: | ------ | ----------: | ------- | -------- |
| 100000 | present | 1 | false | **しない** |
| 100003 | present | 2 | true | **しない** |
| 100004 | present | 2 | true | **しない** |
| 100005 | present | 1 | false | **しない** |

> 事実: 4ID はすべて DB に存在する。地図キャンペーンはこれらを置き換えず、拡大情報源として扱う（Decision / 運用方針 §11.5）。

---

## 5. Human 再測欄（空欄テンプレ）

実測環境が異なる場合、またはキャンペーン途中の再測用。

| 項目 | Human記入 |
| ---- | --------- |
| 実測日時 | |
| 環境（local / その他。接続文字列は書かない） | |
| 総件数 | |
| level 分布（要約） | |
| leaf / non-leaf | |
| root `0` 有無 | |
| MVP 4ID 有無 | |
| テーブル / DB サイズ | |
| ホスト空き（任意） | |
| 備考 | |

---

## 6. 後続 runner 向け要点（推論を含む）

> 本節は **着手前棚卸し時点（15件）** の記録である。Human live 途中の最新件数は [live実行結果_途中](./ジャンル地図キャンペーン_live実行結果_途中.md)（#1839）を正とする。

| 区分 | 内容 |
| ---- | ---- |
| 事実（着手前） | root `0` は未登録。現状は `100000` / `100005` 起点の親＋直下 children 相当（計15行） |
| 事実（着手前） | non-leaf は `100000` と `100005` の2件のみ。level≥3 は未取得 |
| 推論（着手前） | Decision 採択どおり BFS 初回は `--genre-ids 0`（1 Run）で root＋直下 children を入れるのが自然 |
| 推論（着手前） | 現状件数 15 ≪ soft 80,000 / hard 100,000。容量は余裕 |
| 禁止 | MVP 4ID の置き換え提案、AI live、定常crontab変更、weekly/daily 親全体実行 |

---

## 7. 関連リンク

| 資料 | 用途 |
| ---- | ---- |
| [ジャンル地図キャンペーン運用枠 Decision](../../../ai-logs/human-decisions/2026-08-03-batch-genre-map-campaign-ops-plan.md) | 起点・1 Run上限・容量 soft/hard・cron非干渉 |
| [楽天Fetch運用方針](./楽天Fetch運用方針.md) §11.5 | 運用方針側のキャンペーン枠要約 |
| [live実行結果_途中](./ジャンル地図キャンペーン_live実行結果_途中.md) | Human live 途中スナップショット（#1839） |
| [MVP fetch_plan Decision](../../../ai-logs/human-decisions/2026-07-31-rakuten-fetch-mvp-fetch-plan.md) | 4ID 承認（置き換えない） |
| Epic #1827 / Task #1831 | 作業計画 |

---

## 8. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-08-03 | #1831: 初版。local Docker 実測（15件）・再測手順・Human再測欄・容量確認コマンドを正本化 |
| 2026-08-03 | #1839: 着手前記録である旨と live 途中結果へのリンクを追加 |
