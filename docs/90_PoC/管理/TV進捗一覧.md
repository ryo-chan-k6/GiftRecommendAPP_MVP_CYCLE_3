# TV進捗一覧

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 配置 | `docs/90_PoC/管理/` |
| 更新日 | 2026-07-22（TV-007 正式 docs 反映） |
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
| TV-005 | `方針のみ` | なし（要起票） | TV-007 Phase2 の依存候補 |
| TV-006 | `方針のみ` | なし（要起票） | TV-007 Phase2 の依存候補 |
| TV-007 | `完了` | Phase1 [#759](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/759) **CLOSED** / Phase2 [#1512](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1512) **CLOSED** / 正式反映 [#1533](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1533) | Phase2 develop 取り込み済み（#1530）。正式 docs は #1533（最終数値は Human Review） |
| TV-008 | `方針のみ` | なし（要起票） | BATCH レーンと exclusive 調整が必要 |
| TV-009 | `方針のみ` | なし（要起票） | — |
| TV-010 | `方針のみ` | なし（要起票） | BATCH-015 Embedding 実装進展と関連し得る |

---

## 3. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-21 | 初版（#1496）。#759 棚卸しを反映 |
| 2026-07-21 | TV-007 を `Phase1取り込み中` に更新（#759 Phase1 develop 取り込み） |
| 2026-07-21 | TV-007 を `Phase1完了（Phase2待ち）` に更新（#1502 マージ・#759 CLOSED） |
| 2026-07-21 | TV-007 を `Phase2取り込み中` に更新（#1512 Epic PR 準備） |
| 2026-07-22 | TV-007 を `完了` に更新（#1530 Phase2 develop 取り込み・#1533 正式 docs 反映） |
