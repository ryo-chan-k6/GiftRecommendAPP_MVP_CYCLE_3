# Lane 1e D1 residual: empty path / GRS-REC-012

| 項目 | 内容 |
| ---- | ---- |
| Date | 2026-07-16 |
| Issue | #1345 |
| Epic | #1344 |
| Related | D1 #1330 S2 |

## 事実

- D1 で `budgetMax=1` / 過大 budget 時に PUB-002 が HTTP 500 `GRS-REC-012` となり SCR-009 未達。
- UT 再現: Matching 対象 0 件 short-circuit 後、本実装 MOD-RECO-021 が `ranked_items is required` で失敗し `GRS-REC-012`。
- 既存 §19 UT は Output Stub が 021 を差し替えており、本番経路の欠落を隠していた。

## 修正内容

1. Orchestrator: Matching 0 件時に空 `RankedItems` を `execution_context` へ供給。
2. Snapshot Builder / Reason Generator: `result_item_count == 0` を正規成功（明細なし）として扱う。
3. Reason `aggregate_outcome`: 生成 0 件は SUCCESS（empty 正規完了）。
4. §19 UT を本実装 021/022/023 配線で回帰確認。

## 手動再検証（2026-07-16）

| 確認 | 結果 |
| ---- | ---- |
| Branch | `develop`（#1345 / #1344 merge 後） |
| API Case A | `budgetMax=1` → HTTP **200** / `resultStatus=empty` / `resultItemCount=0` / `traceId=s2-reverify-a-budgetmax1` |
| API Case B | `budget 9000-10000` → HTTP **200** / `resultStatus=empty` / `resultItemCount=0` / `traceId=s2-reverify-b-9000-10000` |
| UI | SCR-002 → SCR-003 → SCR-009 相当（「おすすめが見つかりませんでした」） |
| 復帰 | 「条件を変更する」→ SCR-002 再表示（入力値保持） |
| 合否 | **`pass`**（S2 合格条件充足） |

secret / `.env` 実値は記載しない。
