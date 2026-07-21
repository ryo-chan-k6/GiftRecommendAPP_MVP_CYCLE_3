# Human Decision Log

## 1. 概要

| 項目          | 内容 |
| ------------- | ---- |
| Log ID        | `2026-07-16-scr-005-public-reason-points-detail-contract` |
| Log種別       | `human-decision` |
| 件名          | SCR-005 MVP のため Public に `reasonPoints` / `reasonDetail` を任意追加する（案 B） |
| 発生日時      | 2026-07-16 |
| 記録日時      | 2026-07-16 |
| 発生元        | SCR-005 画面仕様書 Task（#1390）Human 指示 |
| 関連Issue     | `#1390`（画面仕様）/ `#1389`（親 Epic SCR-005） |
| 親 Epic       | `#1389` `[Epic]SCR-005:推薦理由詳細表示` |
| 関連PR        | （画面仕様 PR 作成・更新後に追記） |
| 重要度        | `high` |
| 状態          | `decided`（Contract Epic 起票・実施は待ち） |

---

## 2. 結論

| 項目 | 決定内容 |
| ---- | -------- |
| MVP 方針 | **案 B** を採用する。Public API-PUB-002 `items[]` に `reasonPoints` / `reasonDetail` を追加してから SCR-005 を完成させる |
| フィールド必須度 | **任意追加**（必須化しない。後方互換） |
| Contract 形態 | **横断 Contract Epic**（SCR-005 Epic 内・API-PUB-002 子 Task 単独への混入はしない） |
| 着手タイミング | 並行中の他エージェント変更が **すべて develop に merge された後**。その時点で他エージェント Task を止め、Contract Epic を実施する |
| SCR-005 実装 | Contract 反映後に着手（Contract 完了まで blocked） |
| 画面仕様 | `docs/06_実装設計/web/SCR-005_推薦理由詳細表示画面仕様書.md` §8.3 を案 B 前提に更新する |

展開 UI の優先順位（SCR-004 §7.4 と同一）:

1. `reasonPoints`（2〜3）
2. 短い `reasonDetail`
3. 必要時のみ `cautionNote`
4. カード上要約・バッジ再掲は最小限
5. いずれも薄い場合は案内文

---

## 3. human-decision として記録する理由

- SCR-005 Epic の Human 判断点（要約再掲 vs Contract 拡張）の採否である
- OpenAPI / api / web / docs に横断影響があり、通常 SCR-005 Task に混在できない
- API設計方針書 §18.3（表示対象）と現行 Public 契約（未定義）のギャップ解消方針を確定する必要がある

---

## 4. 選択肢と採否

| 案 | 概要 | 採否 |
| --- | ---- | ---- |
| A | Public 既存フィールドのみで SCR-005 MVP を充足（要約再掲＋案内） | 不採用 |
| **B** | Public に `reasonPoints` / `reasonDetail` を追加してから SCR-005 を完成 | **採用** |

補足（Contract 形態）:

| 案 | 概要 | 採否 |
| --- | ---- | ---- |
| API-PUB-002 配下の子 Task のみ | 既存 Epic #357 配下で契約変更 | 不採用（Human は横断 Contract Epic を希望） |
| **横断 Contract Epic** | Public Reason 表示契約として独立 Epic | **採用**（着手は develop 安定後） |

---

## 5. Human 承認

| 項目 | 内容 |
| ---- | ---- |
| 承認者 | Human（チャット指示 2026-07-16） |
| 承認日 | 2026-07-16 |
| 承認内容 | 案 B・任意追加・横断 Contract Epic・並行作業 develop merge 後に実施 |

---

## 6. 後続アクション

| # | アクション | 担当 | 状態 |
| - | ---------- | ---- | ---- |
| 1 | SCR-005 画面仕様書を案 B 前提に更新 | Worker（#1390） | 実施中 |
| 2 | 横断 Contract Epic 用の影響整理（cross-cutting log）を残す | Worker（#1390） | 実施中 |
| 3 | 並行エージェント作業の develop merge 完了を待つ | Human | 待ち |
| 4 | 他エージェント Task を止め、横断 Contract Epic を `/create-contract-task` 等で起票・実施 | Human / Orchestrator | 未着手 |
| 5 | Contract merge 後に SCR-005 実装・単体テスト Task | Worker（#1389 配下） | Contract 待ち |

---

## 7. 関連ドキュメント

| ドキュメント | 関係 |
| ------------ | ---- |
| [SCR-005_推薦理由詳細表示画面仕様書.md](../../docs/06_実装設計/web/SCR-005_推薦理由詳細表示画面仕様書.md) | 画面側正本（§8.3） |
| [API設計方針書.md](../../docs/05_アプリケーション設計/アプリ/api/API設計方針書.md) §18.3 | Public 表示対象に両フィールド記載済み |
| [API-PUB-002_レコメンド実行API契約仕様書.md](../../docs/06_実装設計/api/API-PUB-002_レコメンド実行API契約仕様書.md) | Contract 更新対象 |
| [2026-07-16 Contract Epic prep](../cross-cutting/2026-07-16-public-reason-points-detail-contract-epic-prep.md) | 起票用影響整理 |
