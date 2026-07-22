# TV進捗一覧

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 配置 | `docs/90_PoC/管理/` |
| 更新日 | 2026-07-22（TV-007 Phase3 Epic PR 準備） |
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
| TV-005 | `方針のみ` | なし（要起票） | Phase3 の外部 AI 依存候補（内包しない） |
| TV-006 | `方針のみ` | なし（要起票） | Phase3 の pgvector 依存候補（内包しない） |
| TV-007 | `Phase3取り込み中` | Phase1 [#759](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/759) **CLOSED** / Phase2 [#1512](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1512) **CLOSED** / 正式反映 [#1533](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1533) **CLOSED** / Phase3 [#1535](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1535) | #1536→#1537 Epic 着。Epic PR → develop 取り込み中。`phase_output` 正式反映は別 Task |
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
| 2026-07-22 | TV-007 を `Phase2完了（Phase3待ち）` に更新（#1535 Phase3 起票・#1533 方針反映） |
| 2026-07-22 | TV-007 を `Phase3進行中` に更新（#1536 計測・結果 doc） |
| 2026-07-22 | TV-007 を `Phase3取り込み中` に更新（#1535 Epic PR 準備） |
