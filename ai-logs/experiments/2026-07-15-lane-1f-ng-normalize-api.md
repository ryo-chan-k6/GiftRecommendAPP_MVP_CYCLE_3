# Experiment: レーン1f NG正規化 api 正本化

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-15 |
| Issue | #1324 |
| Epic | #1320 |
| 前提 | Contract #1321 / PR #1322 MERGED |

## 実施内容

- api: `ngText` → `ngKeywords` 派生し INT-002 body へ付与
- reco: Pydantic `NgConditionInput` + `request_mapper` で domain へマップ
- PreFilter: request.ng_text 再抽出を削除（attribute 経路のみ暫定抽出残置）
- 手順書 §10.4.14

## 結果（事実）

| 項目 | 結果 |
| ---- | ---- |
| api UT | **8 passed**（ng-normalize + service） |
| reco UT | **14 passed**（pre_hard_filter + request_mapper） |

## 次（推論）

- Epic #1320 PR → develop（全 Task merge 後）
- attribute 経路の暫定抽出は別整理候補
