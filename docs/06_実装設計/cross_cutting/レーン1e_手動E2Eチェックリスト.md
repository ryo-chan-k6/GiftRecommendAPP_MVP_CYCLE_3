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
| 実施日時 | |
| Branch / commit | |
| HTTP または画面観測 | |
| `resultId` | |
| `resultItemCount` | |
| `traceId` / `requestId`（どちらか） | |
| 合否 | `pass` / `fail` / `blocked` |
| メモ | |

**API 代替確認（UI 不能時の技術観測）:** 手順書 §10.4.2 の `POST /api/v1/recommendations`。UI 必須シナリオの完全代替にはならないが、データ前提の健全性確認として併記可。

---

## 5. S2〜S4 詳細

### S2 0件

| 項目 | 内容 |
| ---- | ---- |
| 狙い | 候補が残らない条件、または API empty |
| 合格 | SCR-009 相当 UI + 条件入力へ戻れる |
| 記録 | 条件概要（個人情報なし）・件数 0・合否 |

### S3 エラー

| 項目 | 内容 |
| ---- | ---- |
| 狙い | api 停止・不正 base URL・強制 5xx 等 |
| 合格 | SCR-008 相当 UI + 条件入力へ戻れる |
| 記録 | 誘発方法（secret なし）・表示文言要約・合否 |

### S4 再検索

| 項目 | 内容 |
| ---- | ---- |
| 狙い | 結果画面から条件入力へ戻る |
| 合格 | SCR-002 再表示 → 再実行可能 |
| 記録 | 導線（ボタン名等）・合否 |

---

## 6. 実行結果サマリ（本 Task）

| ID | 結果 | 実施メモ |
| ---- | ---- | -------- |
| S1 | `blocked` | 2026-07-15: Docker daemon 未起動。DB(`54322`) / Redis / api / web 起動不可。reco :8000 は残留プロセスだが health 503 |
| S2 | `blocked` | 同上（環境前提未達） |
| S3 | `blocked` | 同上 |
| S4 | `blocked` | 同上 |
| S5 | `skipped` | 推奨。環境復旧後に任意実施 |
| S6 | `blocked` | 推奨。API 代替も環境未達 |
| S7 | `out_of_scope` | SCR-006 は別レーン |

### 環境ブロッカー（事実）

| 確認 | 結果 |
| ---- | ---- |
| `docker info` / Docker sock | **失敗**（daemon 未接続） |
| `127.0.0.1:54322` | **閉** |
| Redis `:6379` | **閉** |
| api `:3001` / web `:3000` | **閉** |
| reco `:8000` | LISTEN あるが health **503** |

### Human 判断依頼

1. Docker 起動後に同一 Task で S1〜S4 を再実施してから merge するか  
2. チェックリスト正本のみ develop へ入れ、実行証跡は follow-up Issue にするか  

推奨: **1（Docker 起動後に証跡取得してから merge）**。

---

## 7. 証跡の保管先

| 種別 | 置き場 |
| ---- | ---- |
| チェックリスト（本ファイル） | `docs/06_実装設計/cross_cutting/` |
| 実行メモ | `ai-logs/experiments/` |
| 手順書サマリ | [ローカル開発手順書](./ローカル開発手順書.md) §10.4.15 |

スクショは取得できれば Issue/PR コメントまたは ai-logs にパスのみ記載（バイナリ直 commit は避ける）。**secret / `.env` 実値は禁止**。

---

## 8. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-15 | 初版（Issue #1331）。環境ブロックにより実行は未達 |
