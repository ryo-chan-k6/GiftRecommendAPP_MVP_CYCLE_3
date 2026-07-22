# phase_output soft/hard 暫定据置 + 新定義 secrets 再計測

## 概要

| 項目 | 内容 |
| ---- | ---- |
| Epic | #1552 |
| Task | #1553 |
| 日付 | 2026-07-22 |
| 目的 | Human 判断（暫定据置 + secrets 必須）に基づき、新計測定義での secrets 再計測と正本反映 |

## Human 確定（#1553）

| 項目 | 内容 |
| ---- | ---- |
| soft / hard | **3,000ms / 7,000ms**（案 A **暫定据置**） |
| secrets 再計測 | **必須・実施済** |
| Reason 込み E2E | 6s/8s 同一枠を維持 |
| 最終引き下げ | 後続 Human（新定義実測を踏まえる） |

## local secrets 再計測（新定義）

| 項目 | 値 |
| ---- | -- |
| 環境 | local（WSL2） |
| openai_mode | secrets |
| iterations / warmup | 20 / 2 |
| success | 20 / 20 |
| 定義 | `phase_output` = `result_generated` + `reason_generated`（`response_built` 除外・#1545） |
| 出力（git 未追跡） | `scripts/perf/output-metric-fix-secrets/` |

| 指標 | mock（#1545） | secrets（本計測） |
| ---- | -------------- | ----------------- |
| phase_output p95 (ms) | 105.1 | **109.1** |
| response_built p95 (ms) | 1,233.2 | 3,467.5 |
| Reason E2E p95 (ms) | 1,234.0 | 3,468.2（Go vs 6s/8s） |
| Ranking まで p95 (ms) | 685.1 | 3,083.0（Block vs 内部枠・User Meaning 支配） |

## 所見

- 新定義では mock / secrets とも `phase_output` p95 ≈ **105–109ms**。
- 暫定据置 3s/7s は監視枠として余裕が大きい（最終引き下げは後続 Human・断定しない）。
- secret 実値は成果物に含めない。`.env` は Git 管理外。

## 正本反映

- `docs/06_実装設計/reco/MOD-RECO-001_Recommendation Orchestratorモジュール仕様書.md` §13.2 / §13.2.5 / §16
- `docs/03_ドメイン要件定義/非機能要件定義書/性能要件（バックエンド）.md` §4.1 / §5
- `docs/90_PoC/性能フィジビリティ/設計反映メモ.md`
- `docs/90_PoC/性能フィジビリティ/Reco性能フィジビリティ検証結果_Phase3_reason_e2e.md` §3.3.3 / §5
