# Feature生成性能検証結果（TV-009）

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | PoC 検証結果 |
| 検証ID | TV-009 |
| 方針 | [TV-009_Feature生成性能](../計画/TV要件・実施方針/TV-009_Feature生成性能.md) |
| 関連 Epic / Task | [#1578](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1578) / [#1580](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1580) |
| 計測日 | 2026-07-23（JST） / `measured_at_utc=2026-07-22T15:48:14Z` |
| 設計反映メモ | [設計反映メモ_TV-009](./設計反映メモ_TV-009.md) |

**注意:** 本結果の Go / Adjust / Block は **Feature 生成ロジック単体** の暫定判定である。Reco E2E / User Meaning（外部 AI）は TV-007 / TV-005 を正とする。

---

## 2. 実施概要

| 項目 | 内容 |
| ---- | ---- |
| ハーネス | `scripts/perf/feature_generation_bench.py` |
| 環境 | local（apps/reco `uv`） |
| モード | in-memory（DB / OpenAI 非使用） |
| User | `UserFeatureGenerator`（MOD-RECO-007） |
| Item | `ItemFeatureGenerator`（MOD-RECO-027）。概念数=5 |
| 反復 | iterations=50 / warmup=5 |
| apps/** | 変更なし |
| apps/batch | 変更なし（BATCH-012 ジョブ全体は未計測） |

### 2.1 TV-007 との切り分け（事実）

| 観点 | TV-009（本結果） | TV-007 `user_feature` |
| ---- | ---------------- | --------------------- |
| 計測単位 | Feature merge / normalize / rule 適用 | Semantic〜Embedding（外部 AI 含む）合算 |
| 典型 p95 | sub-ms | 数百 ms〜数秒（secrets） |
| 目的 | Feature 生成そのもののコスト | パイプライン性能・SLO |

---

## 3. 応答時間

| target | p50 (ms) | p95 (ms) | max (ms) |
| ------ | -------- | -------- | -------- |
| user_feature_generator | 0.013 | **0.015** | 0.029 |
| item_feature_generator | 0.040 | **0.043** | 0.065 |

**解釈（事実）:** Feature 生成ロジック単体はいずれも 0.1 ms 未満。TV-007 で観測された `user_feature` 超過の主因ではない。

**解釈（推論）:** Online / Batch の責務設計上、Feature 生成は現状ボトルネック候補から外してよい。BATCH-012 の queue / DB I/O 込みは未計測のため、件数スケール時は別途確認が必要。

---

## 4. 判定

| ラベル | 判定 | 根拠 |
| ------ | ---- | ---- |
| **Go** | 暫定採用 | Feature 単体は致命懸念なし。TV-007 の外部 AI 支配結論と整合 |
| Adjust | — | 現行実装の Feature 生成を覆す必要は見当たらない |
| Block | — | なし |

### 4.1 残リスク

| リスク | 扱い |
| ------ | ---- |
| BATCH-012 ジョブ全体（queue / DB） | 未計測。必要時は別 Task（TV-008 連携） |
| 大量概念・ルール規模 | 本計測は概念 5 件近似。拡大時は再計測 |

---

## 5. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-23 | 初版（#1580）。in-memory 計測・暫定 Go |
