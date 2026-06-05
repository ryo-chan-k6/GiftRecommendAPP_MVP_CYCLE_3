# Human Decision Log

## 1. 概要

| 項目          | 内容 |
| ------------- | ---- |
| Log ID        | `2026-06-05-api-int-002-reason-summary-reason-data-required-scope` |
| Log種別       | `human-decision` |
| 件名          | API-INT-002 Internal `reasonSummary` / `reasonData` の必須・任意 |
| 発生日時      | 2026-06-05 |
| 記録日時      | 2026-06-05 |
| 発生元        | spike Task（human-led） |
| 関連Issue     | `#376` |
| 親 Epic       | `#366` |
| 関連PR        | （PR 作成後に追記） |
| 重要度        | `high` |
| 状態          | `resolved` |

---

## 2. 結論

Internal API（API-INT-002）における Reason 関連フィールドの契約を以下とする。

### 2.1 Item レベル（`data.resultItems[]`）

| 条件 | `reasonSummary` | `reasonStatus` | Item 存続 |
| ---- | --------------- | -------------- | --------- |
| `execution.includeReason=false` | 省略（非返却または null） | 省略 | — |
| `includeReason=true` かつ Reason 成功 | **必須**（非空 string。汎用 Reason §17.2 含む） | `completed` | 存続 |
| `includeReason=true` かつ Reason **生成フェーズのみ**失敗 | **省略または null** | `failed` | **存続**（Ranking 結果は維持） |

| 項目 | 方針 |
| ---- | ---- |
| `recommendationReasonId` | Reason 永続化時は成功 Item で返却（推奨）。`failed` 時は省略 |
| `reasonBadges` / `cautionNote` | 任意。成功時のみ返却可 |
| `reasonStatus` 値域（MVP） | `completed` / `failed` |
| Run `resultStatus` | Item 単位 Reason 失敗のみでは Run 全体を failed にしない。複数 Item で部分失敗時は `partial` 可（Recommendation Result 定義書 §7） |

### 2.2 Run レベル（`data.reasonData`）

| 項目 | 方針 |
| ---- | ---- |
| 必須度 | **任意**（契約上 `false`） |
| 返却推奨 | `includeReason=true` かつ（`includeDebugInfo=true` **または** `execution.mode=evaluation`） |
| 責務 | Item 表示用フィールド（`resultItems[].reasonSummary` 等）とは別に、Reason 生成の**内部詳細**（`reasonDetail` / `reasonPoints` / `reasonBasis` 等）を api・評価向けにまとめる |
| 構造 | `ReasonData` = `{ "items": ReasonDataItem[] }`。各要素は `recommendationResultItemId` で `resultItems[]` と対応 |
| Public | **非表面化**（api は `reasonData` を Public Response へ渡さない） |

契約仕様書への反映: `docs/06_実装設計/api/API-INT-002_Reco推薦実行API契約仕様書.md` §7.3.2、§7.3.8、§14.1 No.4。

---

## 3. human-decision として記録する理由

- 契約仕様書 §14 未決 No.4 は **Human Review** の判断が必要とされていた
- Reason 失敗時の Item 存続・Public 露出範囲は API-PUB-002・UI に影響する
- `reasonData` と `resultItems[]` の責務境界が OpenAPI / 実装 Task の入力となる

---

## 4. 選択肢と採否

| 案 | 概要 | 採否 |
| --- | ---- | ---- |
| A | Item: `includeReason=true` 成功時 `reasonSummary` 必須、Reason のみ失敗時省略＋Item 存続。Run: `reasonData` 任意、debug/evaluation 時推奨。詳細は §7.3.8 | **採用** |
| B | Reason 失敗時も空文字 `reasonSummary:""` を必須 | 不採用（UI が空理由を表示しうる） |
| C | Reason 失敗 Item を `resultItems` から除外 | 不採用（Recommendation Result §11.2 と矛盾） |
| D | Run レベル `reasonData` を `includeReason=true` で常時必須 | 不採用（ui モードのペイロード肥大・Public 非表面化方針と二重管理） |

---

## 5. Human 承認

| 項目 | 内容 |
| ---- | ---- |
| 承認者 | Human（Issue #376 spike 作業。PR Human Review で最終確認） |
| 承認日 | 2026-06-05 |
| 承認内容 | 案A（Item 条件付き必須 + reasonData 任意/debug 推奨）を確定方針とする |

---

## 6. 後続への引き渡し

| 後続 Task | 入力 |
| --------- | ---- |
| OpenAPI Contract Task | `ReasonData` / `ReasonDataItem`、Item `reasonStatus` enum、`reasonSummary` conditional required |
| API-INT-002 実装仕様書 | Reason フェーズ失敗時の reco 応答、api→Public 変換（reasonSummary のみ抽出） |
| API-PUB-002 契約仕様書 | Public 返却は `reasonSummary` / `reasonBadges` / `cautionNote` のみ（reasonData 非露出） |

---

## 7. 関連正本

| ドキュメント | 参照 |
| ------------ | ---- |
| API-INT-002 契約仕様書 | §7.3.2、§7.3.8、§14.1 |
| Reason生成定義書 | §5（出力）、§14（reason_basis）、§17（失敗時） |
| Recommendation Result 定義書 | §11.2（Reason 失敗時 Item 存続） |
| API設計方針書 | §21.3（reasonData 内部項目） |
| Issue #376 | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/376 |
