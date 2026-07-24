# TV-006: pgvector検索性能

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 検証ID | TV-006 |
| 検証名 | pgvector検索性能 |
| 定義正本 | [全体テスト計画書](../../../05_アプリケーション設計/テスト/全体テスト計画書.md) §7.1.2 |
| 全体計画 | [技術検証全体計画](../技術検証全体計画.md) |
| 進捗 | [TV進捗一覧](../../管理/TV進捗一覧.md) |
| 結果の既定置き場 | `docs/90_PoC/技術検証結果/` |
| 結果 | [TV-006_pgvector検索性能検証結果](../../技術検証結果/TV-006_pgvector検索性能検証結果.md) |

---

## 2. 要件（確認すること）

| 観点 | 内容 |
| ---- | ---- |
| 主な確認内容 | 件数別検索時間、index効果、類似検索速度 |
| 判断結果の反映先 | DB設計、Retrieval設計 |

開始・終了条件の共通枠は全体テスト計画書 §7.1.4 / §7.1.5 に従う。

---

## 3. 実施方針

段階は全体計画 §5（S0〜S4）に従う。

| 段階 | 本TVでの実施内容 | 状態（2026-07-22） |
| ---- | ---------------- | ------------------ |
| S0 | 既存 Issue / スクリプト / 結果の有無を棚卸し | 完了 |
| S1 | 本方針書の充足・合格/不合格の判断基準を具体化 | 完了（件数 100/500/1,000・HNSW あり/なし・top_k 5/20） |
| S2 | 計測スクリプト（`pgvector_search_bench.py`） | 完了 |
| S3 | local ephemeral DB で実行し結果を記録 | 完了（暫定 **Go**） |
| S4 | 設計反映メモ（最小）。正式 docs 更新は別 Task | 完了（メモ作成） |

- TV-007 Phase2 の Retrieval 重点リスクと直結する。
- ephemeral / test DB 上で件数スケールを測る。production 禁止。

---

## 4. 検証方針

| 項目 | 方針 |
| ---- | ---- |
| 環境 | local / ephemeral。production 禁止 |
| データ | 検証用合成ベクトル（`vector(1536)`）。個人情報・本番データを使わない |
| 記録 | 件数・index 有無・top_k・p50/p95、EXPLAIN の scan 種別。secret / DB URL 実値は記録しない |
| CI | 通常 PR CI の必須ゲートにしない |
| 判定 | Go（致命懸念なし）/ Adjust（設計調整要）/ Block（成立困難）を明記 |

---

## 5. 関連Issue / 成果物

| 種別 | 状態（2026-07-23） |
| ---- | ------------------ |
| Epic（本体） | [#1571](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1571) **CLOSED** |
| Task（本体） | [#1572](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1572) **CLOSED** |
| Epic（後続 1万件超） | [#1586](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1586) |
| Task（後続 1万件超） | [#1574](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1574) |
| 結果レポート（〜1,000） | [技術検証結果](../../技術検証結果/TV-006_pgvector検索性能検証結果.md) |
| 結果レポート（1万件超） | [後続 1万件超](../../技術検証結果/TV-006_後続_1万件超_pgvector検索性能検証結果.md) |
| ハーネス | `scripts/perf/pgvector_search_bench.py` |

---

## 6. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-21 | 初版方針（#1496） |
| 2026-07-22 | S0〜S4 実施・結果 doc 反映（#1572） |
| 2026-07-23 | 後続 1万件超（#1586 / #1574）・テストデータ計測結果を追記 |
