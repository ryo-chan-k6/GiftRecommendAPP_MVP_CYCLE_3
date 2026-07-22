# phase_output 引き下げ AI 推奨案（GHA secrets 再計測）

## 概要

| 項目 | 内容 |
| ---- | ---- |
| Epic | #1552 |
| Task | #1553 |
| 日付 | 2026-07-22 |
| 目的 | GHA secrets 再計測後、`phase_output` soft/hard の AI 推奨案を整理（採否は Human Review） |

## AI 推奨案（#1553・Human Review で採否確定）

| 項目 | 値 |
| ---- | -- |
| soft（監視） | **500ms** |
| hard | **2,000ms** |
| 旧案 A（暫定据置） | 3,000 / 7,000ms → **廃止を推奨** |
| Reason 込み E2E | 6s/8s 同一枠維持を推奨 |

## 新定義再計測サマリ

| 計測系 | phase_output p95 (ms) | phase_output max (ms) | Reason E2E p95 | 判定（6s/8s） |
| ------ | --------------------- | --------------------- | -------------- | ------------- |
| local mock | 105.1 | — | 1,234 | Go |
| local secrets | 109.1 | 111 | 3,468 | Go |
| **GHA secrets** | **241.4** | **286** | 3,593 | Go |

GHA Run: https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/29898487164

## 推奨根拠（事実・計測）

- 新定義（#1545: `response_built` 除外）の観測帯は p95 ≈ **105–241ms**
- soft **500ms** ≈ 最悪 p95 の約 2 倍（SLO 監視）
- hard **2,000ms** ≈ 最悪 p95 の約 8 倍（スパイク・将来 Reason LLM refinement ON 余裕）
- 本計測は Reason LLM refinement **OFF** 前提。ON 時は再計測
- 数値の最終採否は本 PR の Human Review

## 正本反映

- MOD-RECO-001 §13.2 / §13.2.5 / §16（AI 推奨案として記載）
- 性能要件（バックエンド）§4.1 / §5
- 設計反映メモ
- Phase3 結果 doc §3.3.4 / §5

secret 実値は成果物に含めない。
