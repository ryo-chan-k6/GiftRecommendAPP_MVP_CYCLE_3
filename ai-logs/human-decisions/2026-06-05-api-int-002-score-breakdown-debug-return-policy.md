# Human Decision Log

## 1. 概要

| 項目          | 内容 |
| ------------- | ---- |
| Log ID        | `2026-06-05-api-int-002-score-breakdown-debug-return-policy` |
| Log種別       | `human-decision` |
| 件名          | API-INT-002 scoreBreakdown / debugPayload 返却条件 |
| 発生日時      | 2026-06-05 |
| 記録日時      | 2026-06-05 |
| 発生元        | spike Task（human-led） |
| 関連Issue     | `#375` |
| 親 Epic       | `#366` |
| 関連PR        | （未作成） |
| 重要度        | `high` |
| 状態          | `resolved` |

---

## 2. 結論

Internal API（API-INT-002）における `scoreBreakdown`（Item 単位）と `debug_payload`（Run 単位・API 上は `metadata.debugPayload`）の返却条件を以下とする。

### 2.1 用語

| 用語 | 定義 |
| ---- | ---- |
| debug返却条件 | `execution.mode = evaluation` **OR** `execution.includeDebugInfo = true` |
| 推奨返却 | 契約上必須ではない。欠落しても HTTP 200 を維持する |

`batch` mode 単独では debug返却条件を満たさない（Offline Evaluation は `mode=evaluation` を使用。インターフェース一覧 IF-SHARED-004 参照）。

### 2.2 返却条件マトリクス

| mode | includeDebugInfo | resultItems[].scoreBreakdown | data.metadata.debugPayload |
| ---- | ---------------- | ---------------------------- | -------------------------- |
| ui | false | 省略 | 省略 |
| ui | true | 推奨 | 推奨 |
| evaluation | false / true | 推奨 | 推奨 |
| batch | false | 省略 | 省略 |
| batch | true | 推奨 | 推奨 |

### 2.3 debugPayload マッピング

| ドメイン | Internal API |
| -------- | -------------- |
| `debug_payload`（Recommendation Result 定義書） | `data.metadata.debugPayload`（Run 単位・open object） |

推奨キー（MVP・列挙のみ）: `evalCaseId`, `configName`, `versionLabel`, `modelVersionId`, `rankingConfigVersionId`, `phaseSummary`。追加キーは許容する。

> **改定（2026-06-10 / Task #463）:** Semantic Config 参照は旧 `semanticConfigVersionId` から **`configName` + `versionLabel` composite** へ更新。API-INT-002 契約仕様書 §7.3.8 と整合。

### 2.4 欠落時の tolerant 処理

| 項目 | 方針 |
| ---- | ---- |
| HTTP Status | **200 維持**（Validation エラーにしない） |
| 内部記録 | Recommendation Result 定義書 §13.1 `SCORE_BREAKDOWN_MISSING` 相当を **phase_log / error_log** に記録 |
| `warnings[]` | **載せない**（#373 で確定したパイプライン品質診断用途と分離） |
| Public API | api は `scoreBreakdown` / `metadata.debugPayload` を Public Response へ渡さない（現行維持） |

契約仕様書への反映: `docs/06_実装設計/api/API-INT-002_Reco推薦実行API契約仕様書.md` §7.3.1 / §7.3.2 / §7.3.8、§14.1 No.3。

---

## 3. human-decision として記録する理由

- 契約仕様書 §14 未決 No.3 は **Human Review** の判断が必要とされていた
- `debug_payload` の API フィールドマッピングが未定義だった
- Contract Gate 前に OpenAPI / 実装 Task への入力を確定する必要がある

---

## 4. 選択肢と採否

| 論点 | 採用案 | 不採用案 |
| ---- | ------ | -------- |
| debugPayload 配置 | `data.metadata.debugPayload` | 独立 top-level フィールド / 今回マッピング見送り |
| 必須度 | 推奨（寛容） | evaluation 時必須 |
| batch mode | ui 同列（省略デフォルト） | evaluation 同列 |
| 欠落 surfacing | ログのみ | `warnings[]` に `SCORE_BREAKDOWN_MISSING` 追加 |
| debugPayload スキーマ | open object + 推奨キー列挙 | MVP で詳細スキーマ固定 |

---

## 5. Human 承認

| 項目 | 内容 |
| ---- | ---- |
| 承認者 | Human（Issue #375 作業者） |
| 承認日 | 2026-06-05 |
| 承認内容 | §2 の返却条件マトリクス・マッピング・tolerant 処理を確定方針とする |

---

## 6. 後続への引き渡し

| 後続 Task | 入力 |
| --------- | ---- |
| OpenAPI Contract Task | `ScoreBreakdown` / `metadata.debugPayload` の optional 定義、返却条件は description で参照 |
| API-INT-002 実装仕様書 | debug返却条件マトリクス、reco 側生成・api 側 Public フィルタ |
| reco 実装 | `includeDebugInfo` / `mode` に応じた scoreBreakdown 生成、ログ記録 |

---

## 7. 関連正本

| ドキュメント | 参照 |
| ------------ | ---- |
| API-INT-002 契約仕様書 | §7.3.8、§14.1 No.3 |
| Recommendation Result 定義書 | §9.2、§13.1 |
| API設計方針書 | §21.3 |
| Task Definition | `prompts/definitions/tasks/api-int-002-score-breakdown-debug-return-policy/spike.yaml` |
