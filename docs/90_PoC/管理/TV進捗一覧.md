# TV進捗一覧

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 配置 | `docs/90_PoC/管理/` |
| 更新日 | 2026-07-24（TV-006 後続・正式 docs 反映 develop 着） |
| 計画正本 | [技術検証全体計画](../計画/技術検証全体計画.md) |

ステータス凡例:

| 値 | 意味 |
| --- | --- |
| `未着手` | S0 未実施 |
| `方針のみ` | 方針書はあるが実行なし |
| `進行中` | S2〜S3 の途中 |
| `Phase1完了（未develop）` | 成果はあるが develop 未着 |
| `Phase1取り込み中` | develop 向け PR で Phase1 成果を取り込み中 |
| `Phase1完了（Phase2待ち）` | Phase1 成果は develop にあり、Phase2 未実施 |
| `Phase2取り込み中` | develop 向け Epic PR で Phase2 成果を取り込み中 |
| `Phase2完了（Phase3待ち）` | Phase2 まで develop 着。Phase3（Reason 込み）未実施 |
| `Phase3取り込み中` | develop 向け Epic PR で Phase3 成果を取り込み中 |
| `Phase3進行中` | Phase3 計測・結果 doc 作成中（Human 判定または Epic 取込待ち） |
| `完了` | 当該 TV の PoC 完了条件を満たし develop に成果あり |
| `保留` | Human 判断待ち / 依存待ち |

---

## 2. 一覧（2026-07-22）

| 検証ID | ステータス | 関連Issue | 備考 |
| ------ | ---------- | --------- | ---- |
| TV-001 | `方針のみ` | なし（要起票） | develop 上に結果 doc なし |
| TV-002 | `方針のみ` | なし（要起票） | 同上 |
| TV-003 | `方針のみ` | なし（要起票） | 同上 |
| TV-004 | `方針のみ` | なし（要起票） | 同上 |
| TV-005 | `完了` | Epic [#1565](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1565) **CLOSED** / Task [#1566](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1566) **CLOSED** | Epic PR #1569 develop 着。暫定 **Go** |
| TV-006 | `完了` | 本体 Epic [#1571](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1571) **CLOSED** / [#1572](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1572) **CLOSED**。後続 Epic [#1586](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1586) **CLOSED** / [#1574](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1574) **CLOSED**。正式 docs [#1591](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1591) **CLOSED** / [#1590](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1590) **CLOSED** | 本体 #1575。後続 1万件超 #1593（テストデータ・暫定 **Go**）。正式 DB/Retrieval 反映 #1594（HNSW `m=16` / `ef_construction=64` 現状維持・DDL 非変更） |
| TV-007 | `完了` | Phase1 [#759](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/759) **CLOSED** / Phase2 [#1512](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1512) **CLOSED** / Phase3 [#1535](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1535) **CLOSED** / 正式反映 [#1532](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1532)・[#1533](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1533) | Phase1〜3 develop 着。#1533 確定値・`phase_output` 正式反映は Epic #1532 で develop 取込 |
| TV-008 | `方針のみ` | なし（要起票） | BATCH レーンと exclusive 調整が必要 |
| TV-009 | `完了` | Epic [#1578](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1578) **CLOSED** / Task [#1580](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1580) **CLOSED** | Epic PR #1585 develop 着。Feature 生成 in-memory・暫定 **Go**。BATCH-012 全体は未計測 |
| TV-010 | `方針のみ` | なし（要起票） | BATCH-015 Embedding 実装進展と関連し得る |

---

## 3. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-21 | 初版（#1496）。#759 棚卸しを反映 |
| 2026-07-21 | TV-007 を `Phase1取り込み中` に更新（#759 Phase1 develop 取り込み） |
| 2026-07-21 | TV-007 を `Phase1完了（Phase2待ち）` に更新（#1502 マージ・#759 CLOSED） |
| 2026-07-21 | TV-007 を `Phase2取り込み中` に更新（#1512 Epic PR 準備） |
| 2026-07-22 | TV-007 を `Phase2完了（Phase3待ち）` に更新（#1535 Phase3 起票・#1533 方針反映） |
| 2026-07-22 | TV-007 を `Phase3進行中` に更新（#1536 計測・結果 doc） |
| 2026-07-22 | TV-007 を `Phase3取り込み中` に更新（#1535 Epic PR 準備） |
| 2026-07-22 | TV-007 を `完了` に更新（#1538 Phase3 develop 着。正式 docs は #1532） |
| 2026-07-22 | TV-005 を `進行中` に更新（#1566 計測・結果 doc。develop 着待ち） |
| 2026-07-22 | TV-005 を `完了`、TV-006 を `進行中` に更新（#1569 merge / #1572 計測） |
| 2026-07-23 | TV-006 Task #1573 Epic 着・Epic PR 準備 |
| 2026-07-23 | TV-006 を `完了`（#1575 develop 着）、TV-009 を `進行中`（#1578）に更新 |
| 2026-07-23 | TV-009 を `完了` に更新（#1582 Epic 着・Epic PR develop 着前提） |
| 2026-07-23 | TV-006 後続 1万件超（#1586 / #1574）着手・テストデータ計測結果を反映 |
| 2026-07-24 | TV-006 後続 #1593・正式 docs #1594 develop 着を反映。関連 Issue を CLOSED 表記に更新 |
