# Experiment: レーン1e 手動 E2E（D1）

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-15 |
| Epic | #1330 |
| Task | #1331 |
| 目的 | S1〜S4 手動 E2E 証跡 |

## 実施内容

1. Docker / Supabase / Redis / reco / api / web 起動
2. seed（masters / test-data）
3. UI + PUB-002 でシナリオ実行

## 結果（事実）

| ID | 結果 | 根拠 |
| ---- | ---- | ---- |
| S1 | **pass** | UI `resultId=4314c45c-…` 件数1・¥4,320。API `traceId=d1-manual-e2e-s1-001` count=1 |
| S2 | **fail** | 0件狙いが HTTP 500 `GRS-REC-012`（SCR-009 未達） |
| S3 | **pass** | api 停止 → 「エラー」UI → 「条件入力へ戻る」 |
| S4 | **pass** | 「条件を変更して再検索」→ SCR-002 |
| S5 | **pass** | 理由詳細展開 |
| S6 | **pass** | alcohol NG で焼き菓子のみ |

### Residual

- SCR-001 `/`: HomePage client exception（自動化）
- 画像プレースホルダ

## 環境

| 項目 | 値 |
| ---- | ---- |
| develop tip（実行） | `5bcdc6e0` |
| Docker | OK |
| DB / Redis / api / reco / web | 起動確認済み |

## 次（推論）

- D1 は S2 を residual Issue 化して Close 許容が妥当
- SCR-001 `/` 例外は web 別 Issue
