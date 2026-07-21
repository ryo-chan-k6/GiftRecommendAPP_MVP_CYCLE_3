# TV-007: Reco性能フィジビリティ

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 検証ID | TV-007 |
| 検証名 | Reco性能フィジビリティ |
| 定義正本 | [全体テスト計画書](../../../05_アプリケーション設計/テスト/全体テスト計画書.md) §7.1.2 |
| 全体計画 | [技術検証全体計画](../技術検証全体計画.md) |
| 進捗 | [TV進捗一覧](../../管理/TV進捗一覧.md)（TV-007 = `完了`） |
| 棚卸し | [759_Reco性能フィジビリティ棚卸し_2026-07-21](../../管理/759_Reco性能フィジビリティ棚卸し_2026-07-21.md) |
| 関連 Epic | Phase1 [#759](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/759) / Phase2 [#1512](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1512) / 正式反映 [#1533](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1533) |
| 結果の既定置き場 | `docs/90_PoC/性能フィジビリティ/` |

---

## 2. 要件（確認すること）

| 観点 | 内容 |
| ---- | ---- |
| 主な確認内容 | 入力解析〜Rankingまでの概算時間 |
| 判断結果の反映先 | Reco設計、非機能設計（性能要件 §5 / MOD-RECO-001 §13.2） |
| 暫定判定対象 | soft 2,000ms / hard 4,000ms（MOD-RECO-001 §13.2 現行値。最終採否は Human Review） |

Reason 生成は参考計測とし、TV-007 主対象からは除外する（#759 計画書方針）。

---

## 3. 実施方針

全体計画の S0〜S4 に加え、本 TV は **Phase1 / Phase2** を用いる（#759 計画書）。

| フェーズ | 対応段階 | 内容 | 現状（2026-07-22） |
| -------- | -------- | ---- | ------------------ |
| Phase1 | S1〜S3（skeleton） | ハーネス整備、skeleton 実測、設計試算、設計反映メモ | 完了済み（#1502 develop 取り込み） |
| Phase2 | S3（live） | 実装済みパイプラインの実測、Go/Adjust/Block | 完了済み（#1512 / #1530 develop 取り込み） |
| 正式反映 | S4 後の別 Task | 性能要件 / Orchestrator 仕様の正式更新 | **#1533 で正本反映済み**（最終数値は Human Review 確定待ち） |

```mermaid
flowchart LR
  P1[Phase1 skeleton] --> Land[develop反映]
  Land --> P2[Phase2 live]
  P2 --> Formal[正式docs 別Task]
```

### 3.1 依存

| 依存 | 扱い |
| ---- | ---- |
| TV-005 / TV-006 | Phase2 live の精度向上に有用。内包最小計測か別 TV 先行かは Human 判断 |
| MOD-RECO 実装 | live 定義の前提。#260 CLOSED 後も実装が進んでいるため、Phase2 着手前に計測境界を再確認する |
| BATCH レーン | path 衝突は小さい。計測環境の取り合いに注意 |

---

## 4. 検証方針

| 項目 | 方針 |
| ---- | ---- |
| 環境 | local / GHA Layer2（`perf-feasibility-reco.yml`）。production 禁止 |
| モード | Phase1: `skeleton`。Phase2: `live`（ephemeral DB / mock or secrets） |
| 指標 | フェーズ別・全体 wall-clock（p50 / p95）。必要に応じ候補件数スケール |
| 記録 | `性能フィジビリティ/` に計画・結果・設計反映メモ |
| CI | 通常 PR CI 必須ゲートにしない |
| 判定 | soft/hard に対する Go / Adjust / Block（Phase2 実測根拠） |
| 実装変更 | `apps/reco/src/**` は原則禁止（計測のための変更が必要なら別 Issue） |

詳細手順の正本: [Reco性能フィジビリティ検証計画書](../../性能フィジビリティ/Reco性能フィジビリティ検証計画書.md) / [scripts/perf/README.md](../../../../scripts/perf/README.md)

### 4.1 Phase2 live 計測境界（#1513）

| 境界 | 内容 |
| ---- | ---- |
| 実行 | `RecommendationOrchestrator` + `CompositionMode.PRODUCTION`（HTTP 非経由） |
| TV-007 主対象 | 入力解析〜 Ranking。Reason は参考 |
| DB | ephemeral Supabase + master / test-data seed（`test-reco-quality.yml` 同型） |
| OpenAI | `mock`（scaffold）または `secrets`（`scripts/perf/openai_bench_clients.py` 差込。apps/reco 非改修） |
| 判定 | soft 2,000ms / hard 4,000ms（p95）。最終採用は Human Review |
| 件数スケール | test-data seed は item 3 件。100/500/1,000 件スケールは追加 seed が必要（未実施理由を結果 doc に明示可） |

---

## 5. 関連Issue / 成果物

| 種別 | 状態 |
| ---- | ---- |
| Phase1 Epic | #759 CLOSED（#1502 マージ時） |
| Phase1 子 Task | #761 / #762 / #763 CLOSED |
| Phase2 Epic | #1512 |
| Phase2 Task | #1513（`poc-live-verification`） |
| 結果ドキュメント | [検証計画書](../../性能フィジビリティ/Reco性能フィジビリティ検証計画書.md) / [Phase1結果](../../性能フィジビリティ/Reco性能フィジビリティ検証結果_Phase1.md) / [設計反映メモ](../../性能フィジビリティ/設計反映メモ.md) / Phase2 live 結果（#1513） |

---

## 6. 次アクション候補

1. #1513 live 計測・結果 doc・設計反映メモ更新
2. Human Review で §13.2 現行値の最終採用可否を判断（内部 Go / 外部 AI Adjust 分離を含む）
3. 正式 docs 更新 Task の起票（性能要件 §5 / MOD-RECO-001 §13.2）

---

## 7. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-21 | 初版方針。#759 棚卸しを反映（#1496） |
| 2026-07-21 | Phase1 develop 取り込みに合わせて現状・次アクションを更新 |
| 2026-07-21 | Phase2 live 計測境界（#1512/#1513）を追記 |
