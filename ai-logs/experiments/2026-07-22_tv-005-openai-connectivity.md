# TV-005 外部AI API疎通 実験ログ（#1566）

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-22 |
| Issue | #1566 |
| 正本結果 | `docs/90_PoC/外部API疎通検証/外部AI_API疎通検証結果.md` |

## 実施

| モード | iterations | embed p95 (ms) | chat p95 (ms) | 概算 USD | 備考 |
| ------ | ---------- | -------------- | ------------- | -------- | ---- |
| mock | 20 | 2.3 | 5.3 | （模擬） | failure probe: 401/429/timeout |
| secrets | 10 (+warmup1) | 654.4 | 2796.3 | ≈0.00033 | failure probe: invalid model → 404 |

## メモ

- rate limit 大量誘発は未実施
- secret 実値は本ログに含めない
- 詳細・判定は結果 doc を正とする
