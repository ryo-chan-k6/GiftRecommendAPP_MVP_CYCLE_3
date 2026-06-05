# Human Decision Log

## 1. 概要

| 項目          | 内容 |
| ------------- | ---- |
| Log ID        | `2026-06-05-api-int-002-internal-401-public-map-policy` |
| Log種別       | `human-decision` |
| 件名          | API-INT-002 Internal 認証エラー（`GRS-AUTH-*`）の Public マップ方針 |
| 発生日時      | 2026-06-05 |
| 記録日時      | 2026-06-05 |
| 発生元        | spike Task（human-led） |
| 関連Issue     | `#374` |
| 親 Epic       | `#366` |
| 関連PR        | `#377` |
| 重要度        | `high` |
| 状態          | `resolved` |

---

## 2. 結論

api（`apps/api`）が reco（API-INT-002）から受け取る Internal の `GRS-AUTH-*`（HTTP 401/403）は、Public API（API-PUB-002）へ **そのまま返却しない**。

| 項目 | 確定方針 |
| ---- | -------- |
| Public HTTP Status | **500** |
| Public `error.code` | **`GRS-REC-002`** |
| Public `error.message` | エラーコード定義書の `GRS-REC-002` ユーザー向け文言 |
| `meta.traceId` / `meta.requestId` | 維持 |
| error_log（内部） | 原文の `GRS-AUTH-*`・Internal HTTP Status・upstream を保持 |
| MVP の Public 401 | API-PUB-002 では定義しない（匿名 Public。後続認証は別 Issue） |

契約仕様書への反映: `docs/06_実装設計/api/API-INT-002_Reco推薦実行API契約仕様書.md` §8.2.1、§14.1 No.2。

---

## 3. human-decision として記録する理由

- 契約仕様書 §14 未決 No.2 は **Human + api 実装** の判断が必要とされていた
- Public への `GRS-AUTH-*` 露出はセキュリティ・UX（MVP 匿名）に影響する
- 後続の実装仕様書・MOD-API-013・API-PUB-002 契約の入力となる

---

## 4. 選択肢と採否

| 案 | 概要 | 採否 |
| --- | ---- | ---- |
| A | 500 + `GRS-REC-002`、`GRS-AUTH-*` 非露出、error_log に原文 | **採用** |
| B | 500 + `GRS-COM-999` | 不採用（REC 系メトリクス・UI 分類から外れる） |
| C | 503 + `GRS-COM-003` | 不採用（`GRS-AUTH-*` は retryable:false。ユーザー再試行は無効） |
| D | Public 401 + `GRS-AUTH-*` 透過 | 不採用（契約 §8.2・MVP 匿名 Public と矛盾） |

---

## 5. Human 承認

| 項目 | 内容 |
| ---- | ---- |
| 承認者 | Human（Issue #374 作業者） |
| 承認日 | 2026-06-05 |
| 承認内容 | 案A（500 + `GRS-REC-002`）を確定方針とする |

---

## 6. 後続への引き渡し

| 後続 Task | 入力 |
| --------- | ---- |
| API-INT-002 実装仕様書 | §8.2.1 マップ表、reco-client エラーハンドリング、api 事前 Key 検証 |
| API-PUB-002 契約仕様書 | Public Error 一覧に「Internal 認証失敗は `GRS-REC-002` に集約」と参照 |
| api 実装 | MOD-API-013 変換テーブル、reco 401 モックの単体テスト |

---

## 7. 関連正本

| ドキュメント | 参照 |
| ------------ | ---- |
| API-INT-002 契約仕様書 | §8.2、§8.2.1、§14.1 |
| エラーコード定義書 | §3.1、§9、§24 |
| API設計方針書 | §11.1–11.3（MVP 匿名 Public） |
| インターフェース一覧 | §15 補足 |
| Issue #374 | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/374 |
