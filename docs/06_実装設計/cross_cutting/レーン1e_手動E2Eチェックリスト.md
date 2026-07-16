# レーン1e 手動 E2E チェックリスト（D1）

## 1. 目的

画面遷移図の主導線どおり、ローカル環境で **SCR-001 → SCR-002 → SCR-003 → SCR-004（結果あり）** を人手再現し、0件・失敗・再検索の品質分岐を確認する。

本ドキュメントは並列計画 **D1（手動 E2E）** の正本チェックリストである。自動 E2E（D2 / Playwright）は対象外。

| 項目 | 内容 |
| ---- | ---- |
| Epic | #1330 `[Epic]レーン1e:手動E2E検証` |
| Task | #1331 |
| 前提 Epic | #1255 SCR-001 / #1147 SCR-002 / #1236 SCR-004 / #1263 結果あり / #1320 NG 正本化 |
| 手順正本 | [ローカル開発手順書](./ローカル開発手順書.md) §9〜§10.4 |

---

## 2. 前提条件

実行前にすべて満たすこと。

| No | 条件 | 確認方法 |
| -- | ---- | -------- |
| P1 | Docker Desktop（WSL integration）が起動している | `docker info` 成功 |
| P2 | Supabase ローカル DB（54322）が起動している | `./scripts/db/status.sh` |
| P3 | Redis が起動している | `docker compose -f docker-compose.dev.yml ps` 等 |
| P4 | `.env` が存在し `check-env-names.sh --strict` が通る | 実値は docs に書かない |
| P5 | master / test-data seed 済み | `seed-masters.sh` / `seed-test-data.sh` |
| P6 | reco :8000 / api :3001 / web :3000 が疎通 | health / TOP 表示 |
| P7 | develop tip（または D1 作業 Branch）で起動している | `git branch --show-current` |

補助: `./scripts/dev/smoke-check.sh`（利用可能な場合）。

---

## 3. シナリオ一覧

| ID | 区分 | シナリオ | 必須 | 合格条件（要約） |
| ---- | ---- | -------- | ---- | ---------------- |
| S1 | 最小パス | SCR-001 → SCR-002 → SCR-003 → SCR-004（結果あり） | **必須** | `/recommendations/{resultId}` に **1件以上**。順位・商品名・価格が視認できる。`traceId` または `requestId` を記録 |
| S2 | 品質 | SCR-009（0件）相当 | **必須** | 0件 UI（または API `resultItemCount=0`）と、条件入力へ戻れる |
| S3 | 品質 | SCR-008（実行失敗）相当 | **必須** | エラー表示（通信失敗等）と、条件入力へ戻れる |
| S4 | 品質 | 再検索 → SCR-002 | **必須** | 結果画面から条件入力へ戻り再実行できる |
| S5 | 推奨 | SCR-005 理由詳細 | 推奨 | 理由要約/詳細が開ける（未実装なら「未達・別 Issue」） |
| S6 | 推奨 | alcohol NG（`ngText: アルコールはNG`） | 推奨 | ワイン系が除外され件数/内容が妥当（§10.4.12 / 1f） |
| S7 | 任意 | SCR-006 商品詳細 | 任意 | 本 Epic out of scope（別レーン） |

---

## 4. S1 詳細手順（必須・結果あり）

1. web で `/`（SCR-001）を開く  
2. CTA から `/recommendations`（SCR-002）へ遷移する  
3. 関係・用途マスタが表示されることを確認する（PUB-005/006）  
4. 推奨条件例（手順書 §10.4.2）に近い値を入力し実行する  
5. SCR-003（実行中）が表示されることを確認する  
6. SCR-004 `/recommendations/{resultId}` で一覧を確認する  

### S1 記録欄

| 項目 | 記録 |
| ---- | ---- |
| 実施日時 | 2026-07-15（Docker 復旧後再開） |
| Branch / commit | web/api: `develop` `5bcdc6e0` / docs Task: `34f64527`→本更新 |
| HTTP または画面観測 | UI: SCR-002→003→004。SCR-001(`/`) は HomePage webpack 例外で自動化不可のため `/recommendations` から開始 |
| `resultId` | `4314c45c-3663-41eb-a559-7033b8285187`（UI） / API 別実行 `0b14bc8d-3bde-4956-a1b2-e0e291c70667` |
| `resultItemCount` | **1** |
| `traceId` / `requestId`（どちらか） | API: `traceId=d1-manual-e2e-s1-001` / UI 実行はブラウザ Network 未採取 |
| 合否 | `pass`（ただし SCR-001 起点は別途 residual） |
| メモ | 商品「上品な焼き菓子ギフトセット」¥4,320。画像プレースホルダ。Feedback 準備中 |

**API 代替確認:** `POST /api/v1/recommendations` HTTP 200 / `resultItemCount=1` / alcohol NG で item_003 除外。

---

## 5. S2〜S4 詳細

### S2 0件

| 項目 | 内容 |
| ---- | ---- |
| 狙い | 候補が残らない条件、または API empty |
| 合格 | SCR-009 相当 UI + 条件入力へ戻れる |
| 記録 | 条件概要（個人情報なし）・件数 0・合否 |
| 本実行（D1） | `budgetMax=1` および `budget 9000-10000` とも API **HTTP 500** `GRS-REC-012`。`resultStatus=empty` 未達 → SCR-009 UI に到達不能。**合否 `fail`（製品ギャップ）** |
| 修正（#1345） | Matching 0 件 short-circuit 後に空 `ranked_items` を供給し、021/022/023 が empty を正常完了するよう修正。UT で本実装配線の empty 完了を回帰防止。**手動再検証は Human Review 前または後続で実施** |

### S3 エラー

| 項目 | 内容 |
| ---- | ---- |
| 狙い | api 停止・不正 base URL・強制 5xx 等 |
| 合格 | SCR-008 相当 UI + 条件入力へ戻れる |
| 記録 | 誘発: api プロセス停止後に実行。「エラー / レコメンド実行に失敗しました」表示。「条件入力へ戻る」で SCR-002 復帰。**合否 `pass`** |

### S4 再検索

| 項目 | 内容 |
| ---- | ---- |
| 狙い | 結果画面から条件入力へ戻る |
| 合格 | SCR-002 再表示 → 再実行可能 |
| 記録 | 「条件を変更して再検索」→ `/recommendations`。NG テキスト保持を確認。**合否 `pass`** |

---

## 6. 実行結果サマリ（本 Task）

| ID | 結果 | 実施メモ |
| ---- | ---- | -------- |
| S1 | `pass` | SCR-002→003→004。件数1・価格表示。SCR-001(`/`) 例外は #1346 で修正（native `<a>` CTA）。再確認: 例外なく表示・CTA→`/recommendations` |
| S2 | `fail`（D1）→ `#1345` 修正済 | D1 時点は `GRS-REC-012`。#1345 merge 済。手動再検証待ち |
| S3 | `pass` | api 停止→エラー UI→条件入力へ戻る |
| S4 | `pass` | 再検索リンクで SCR-002 復帰 |
| S5 | `pass` | 「理由の詳細」展開で要約表示 |
| S6 | `pass` | alcohol NG で焼き菓子1件（ワイン除外）。API/UI いずれも件数1 |
| S7 | `out_of_scope` | SCR-006 は別レーン |

### Residual / 後続 Issue（起票済）

| 内容 | Issue | 親 Epic |
| ---- | ---- | ---- |
| 0件が `GRS-REC-012` になり SCR-009 未到達 | #1345 | #1344 |
| SCR-001 `/` の client exception（HomePage） | #1346 | #1344 |
| 結果カード画像プレースホルダ | （未起票・低優先） | — |

D1 本体（#1330）は Close 済み。residual 解消は Epic #1344 で追跡する。

---

## 7. 証跡の保管先

| 種別 | 置き場 |
| ---- | ---- |
| チェックリスト（本ファイル） | `docs/06_実装設計/cross_cutting/` |
| 実行メモ | `ai-logs/experiments/` |
| 手順書サマリ | [ローカル開発手順書](./ローカル開発手順書.md) §10.4.15 |
| スクショ | ローカル取得 `d1-s1-result.png`（バイナリは commit しない）。観測は本表に要約 |

**secret / `.env` 実値は禁止**。

---

## 8. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-15 | 初版（Issue #1331）。環境ブロックにより実行は未達 |
| 2026-07-15 | Docker 復旧後に S1/S3/S4/S5/S6 実施。S2 fail・SCR-001 residual を記録 |
| 2026-07-16 | residual を Epic #1344 / Task #1345・#1346 として起票 |
| 2026-07-16 | #1345: Matching 0 件後の empty 経路修正内容を S2 に追記（手動再検証は未実施） |
| 2026-07-16 | #1346: SCR-001 HomePage の `next/link` 起因 client 例外を native `<a>` CTA で解消 |
