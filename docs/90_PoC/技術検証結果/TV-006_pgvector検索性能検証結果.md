# TV-006 pgvector検索性能検証結果

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | PoC 検証結果 |
| 検証ID | TV-006 |
| 方針 | [TV-006_pgvector検索性能](../計画/TV要件・実施方針/TV-006_pgvector検索性能.md) |
| 関連 Epic / Task | [#1571](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1571) / [#1572](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1572) |
| 計測日 | 2026-07-22（JST） / `measured_at_utc=2026-07-22T13:38:42Z` |
| 設計反映メモ | [設計反映メモ](./設計反映メモ_TV-006.md) |

**注意:** 本結果の Go / Adjust / Block は **TV-006（pgvector 類似検索単体）** の暫定判定である。Reco E2E の性能判定は TV-007 を正とする。

---

## 2. 実施概要

| 項目 | 内容 |
| ---- | ---- |
| ハーネス | `scripts/perf/pgvector_search_bench.py` |
| 環境 | local Supabase（`127.0.0.1:54322`）。production 禁止 |
| テーブル | 一時 UNLOGGED `tv006_pgvector_bench`（`vector(1536)`）。本番 `item_embedding` と同次元・同 HNSW 設定 |
| HNSW | `vector_cosine_ops` / `m=16` / `ef_construction=64`（DDL 正本と同値） |
| 件数 | 100 / 500 / 1,000 |
| top_k | 5 / 20 |
| 反復 | iterations=30 / warmup=3 |
| クエリ形状 | `ORDER BY embedding <=> $query::vector LIMIT $top_k`（本番 Retrieval の距離演算と同型。`item` JOIN / filter は対象外） |
| apps/** | 変更なし |

### 2.1 TV-007 との切り分け（事実）

| 観点 | TV-006（本結果） | TV-007 |
| ---- | ---------------- | ------ |
| 計測単位 | pgvector 類似検索単体 | Reco Orchestrator E2E |
| 件数スケール | 100 / 500 / 1,000 | Phase2 は seed 3 件中心 |
| index 比較 | HNSW あり（経路強制） vs なし | E2E 内の一要素 |
| 主目的 | 件数・index 効果 | パイプライン性能・SLO |

### 2.2 計測上の注記（事実）

- 小件数では planner が Seq Scan を選びやすい。HNSW 計測では `enable_seqscan=off` で **index 経路を強制**した。
- seqscan 計測では HNSW を DROP し、`enable_indexscan=off` とした。
- 本番 runtime では planner がコストベースで経路を選ぶ。本結果は「index を使った場合の実効」と「全件距離計算」の対比である。

---

## 3. 検索時間（p50 / p95 / max）

単位: ms。host=`127.0.0.1:54322`。

| scale | index | top_k | p50 | p95 | max | plan |
| ----- | ----- | ----- | --- | --- | --- | ---- |
| 100 | hnsw | 5 | 0.513 | **0.713** | 0.790 | index_scan |
| 100 | hnsw | 20 | 0.509 | **0.687** | 0.957 | index_scan |
| 100 | seqscan | 5 | 0.634 | 0.804 | 1.012 | seq_scan |
| 100 | seqscan | 20 | 0.712 | 1.064 | 1.106 | seq_scan |
| 500 | hnsw | 5 | 1.693 | **2.043** | 2.073 | index_scan |
| 500 | hnsw | 20 | 0.988 | **2.199** | 2.633 | index_scan |
| 500 | seqscan | 5 | 2.998 | 6.459 | 6.985 | seq_scan |
| 500 | seqscan | 20 | 2.553 | 6.004 | 6.187 | seq_scan |
| 1,000 | hnsw | 5 | 1.114 | **2.393** | 2.676 | index_scan |
| 1,000 | hnsw | 20 | 1.021 | **2.142** | 3.048 | index_scan |
| 1,000 | seqscan | 5 | 10.529 | 11.176 | 11.535 | seq_scan |
| 1,000 | seqscan | 20 | 10.267 | 11.693 | 11.794 | seq_scan |

### 3.1 HNSW index 構築時間（参考）

| scale | build_ms |
| ----- | -------- |
| 100 | 17.1 |
| 500 | 243.1 |
| 1,000 | 673.5 |

**解釈（事実）:** 1,000 件・HNSW 経路の検索 p95 は約 **2.1〜2.4 ms**。同一件数の seqscan p95 は約 **11〜12 ms**。件数増に伴い seqscan が悪化し、HNSW の相対効果が大きくなる。

**解釈（推論）:** TV-007 の Retrieval が seed 3 件のみだった未実施ギャップ（件数・index）は、本単体計測で「1,000 件までは致命的ボトルネックにならない」方向の根拠になる。JOIN / filter / 実カタログ分布は別途確認が必要。

---

## 4. 判定

| ラベル | 判定 | 根拠 |
| ------ | ---- | ---- |
| **Go** | 暫定採用 | 推奨前提（100/500/1,000・1536・top_k 5/20・HNSW あり/なし）を満たし、1,000 件 HNSW でも検索 p95 < 5 ms。致命懸念なし |
| Adjust | — | 現状の正式 DDL（HNSW 定義済み）を覆す必要は見当たらない |
| Block | — | 成立困難な兆候なし |

### 4.1 残リスク（明示）

| リスク | 扱い |
| ------ | ---- |
| JOIN + Hard Filter 込みの Retrieval | 本 TV 対象外。TV-007 / 本番経路で別途 |
| 1,000 件超（例: 1万〜） | 未計測。後続 [#1574](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1574) |
| planner が小件数で Seq Scan を選ぶこと | 本番でも起こり得る。コスト差が小さい領域では許容されやすい（推論） |

---

## 5. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-22 | 初版（#1572）。local 計測・暫定 Go |
| 2026-07-23 | 残リスク「1,000 件超」に後続 [#1574](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1574) を紐付け |
