# Planned Start に基づく Status 更新ワークフロー — テストケースと結果

対象ワークフロー: [`.github/workflows/update-projects-status-by-planned-start.yml`](../update-projects-status-by-planned-start.yml)  
正本仕様: [`docs/00_共通/プロジェクト運用ルール/GitHub Actions仕様書/Planned Startに基づくStatus自動更新ワークフロー.md`](../../../docs/00_共通/プロジェクト運用ルール/GitHub%20Actions仕様書/Planned%20Startに基づくStatus自動更新ワークフロー.md)  
判定モジュール: [`.github/scripts/planned-start-status-policy.cjs`](../../scripts/planned-start-status-policy.cjs)

---

## 1. スコープ

| 区分 | 内容 |
| ---- | ---- |
| 本ファイルで扱うテスト | **日付・Status 判定ロジック**（リポジトリに依存しない純粋関数）の単体テスト |
| 別途（手動）で推奨する検証 | GitHub 上で `workflow_dispatch` による **Project 実データ**への適用確認、`PROJECTS_TOKEN` 権限確認 |

---

## 2. テストケース一覧と実施結果

テストランナー: **Node.js**（`node --test`）  
テストファイル: `.github/scripts/planned-start-status-policy.test.cjs`

| ID | 対象 | 入力・前提 | 期待結果 | 実施結果 |
| --- | --- | --- | --- | --- |
| TC-PS-01 | `normalizePlannedStartYmd` | ISO 日時 `2026-05-13T00:00:00Z` | `2026-05-13` | **合格** |
| TC-PS-02 | `normalizePlannedStartYmd` | `null` / 空文字 / 空白のみ | `null` | **合格** |
| TC-PS-03 | `isBacklogStatus` | `Backlog` / `BACKLOG` | `true` | **合格** |
| TC-PS-04 | `shouldPromoteFromBacklogToTodo` | Status=Backlog、Planned=過去日、`todayYmd` 固定 | `true` | **合格** |
| TC-PS-05 | `shouldPromoteFromBacklogToTodo` | Status=Backlog、Planned=当日、`todayYmd` 同一 | `true`（当日 0:00 運用と整合） | **合格** |
| TC-PS-06 | `shouldPromoteFromBacklogToTodo` | Status=Backlog、Planned=未来日 | `false` | **合格** |
| TC-PS-07 | `shouldPromoteFromBacklogToTodo` | Status=Todo（Planned は過去） | `false` | **合格** |
| TC-PS-08 | `shouldPromoteFromBacklogToTodo` | Planned 欠落（`null`） | `false` | **合格** |
| TC-PS-09 | `todayJstYmd` | 固定 `Date` を渡して呼び出し | 戻り値が `YYYY-MM-DD` 形式 | **合格** |

### 2.1 コマンド出力（ローカル実施ログ）

実施日: **2026-05-13**（ローカル環境・リポジトリルート）

```bash
node --test .github/scripts/planned-start-status-policy.test.cjs
```

```
TAP version 13
# Subtest: normalizePlannedStartYmd: ISO を先頭10文字で切る
ok 1 - normalizePlannedStartYmd: ISO を先頭10文字で切る
# Subtest: normalizePlannedStartYmd: 空は null
ok 2 - normalizePlannedStartYmd: 空は null
# Subtest: isBacklogStatus: 大文字小文字無視
ok 3 - isBacklogStatus: 大文字小文字無視
# Subtest: shouldPromote: Backlog かつ予定日が当日以前 → true
ok 4 - shouldPromote: Backlog かつ予定日が当日以前 → true
# Subtest: shouldPromote: 予定日が未来 → false
ok 5 - shouldPromote: 予定日が未来 → false
# Subtest: shouldPromote: Status が Todo なら false
ok 6 - shouldPromote: Status が Todo なら false
# Subtest: shouldPromote: Planned Start 欠落 → false
ok 7 - shouldPromote: Planned Start 欠落 → false
# Subtest: todayJstYmd: 形式が YYYY-MM-DD
ok 8 - todayJstYmd: 形式が YYYY-MM-DD
1..8
# tests 8
# suites 0
# pass 8
# fail 0
```

**総合判定（単体テスト範囲）**: **合格**（8 件すべて成功）。

---

## 3. 統合試験（任意・手動）

| ID | 内容 | 期待結果 |
| --- | --- | --- |
| TC-PS-INT-01 | Actions の **Run workflow** で `workflow_dispatch` 実行 | 対象 Issue のみ Status が Todo に変わる |
| TC-PS-INT-02 | `cron` 相当時刻の前後で JST 当日の解釈 | Summary の JST 当日が期待どおり |

統合試験の結果を記録する場合は、本セクションに **Run URL** と変更した Issue 番号を追記する。

---

## 4. 再実行コマンド（メンテ用）

```bash
cd /path/to/GiftRecommendAPP_MVP_CYCLE_3
node --test .github/scripts/planned-start-status-policy.test.cjs
```
