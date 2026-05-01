# Create branch from issue — `issues` イベント（自動実行）検証結果

対象ワークフロー: [`.github/workflows/create-branch-from-issue.yml`](../create-branch-from-issue.yml)  
正本仕様: `docs/00_共通/プロジェクト運用ルール/GitHub Actions仕様書/ブランチ自動作成ワークフロー.md`  
検証実施: GitHub Actions 上の実ラン（`gh` CLI で Run / Issue コメント / GraphQL を確認）  
記録日時（GitHub 上の Run 基準）: 2026-05-01 07:22–07:25 UTC 前後

---

## 1. スコープ

| 区分 | 内容 |
|------|------|
| 今回の検証 | `on.issues`（`opened` / `labeled` / `unlabeled` / `edited`）による**自動起動**の成否と、Issue コメント・Development リンクの整合性 |
| 対象外（ユーザー完了済み） | `workflow_dispatch` の **dry-run**（本ファイルでは参照のみ） |

---

## 2. テストケース一覧と実施結果

検証に用いた Issue: **#11** — `[Task]: ブランチ自動作成ワークフロー検証`  
（ラベル例: `unit: task`, `type: test`）

| ID | トリガー想定 | 事前条件 | 期待結果 | 実施結果 | 根拠 |
|----|--------------|----------|----------|----------|------|
| TC-ISS-01 | `issues.*`（ラベル不足） | `type:*` のみ等で **`unit:*` なし** | ブランチ作成を行わず、**不足理由の Issue コメント** | **合格** | Issue #11 コメント: 「`unit:*` ラベルが設定されていません。」 |
| TC-ISS-02 | `issues.labeled` 等（必須ラベル充足） | `unit: task` と `type: test` が揃う | **`createLinkedBranch`** 成功、成功コメント、Development にリンク | **合格** | コメント: Branch `test/task-11-branch-auto-creation-workflow-validation` / Base `develop` / Trigger `issues.labeled`。GraphQL `linkedBranches`: 同ブランチ名・`develop` 先端付近の OID |
| TC-ISS-03 | 同一ブランチが既に期待名と一致 | 上記のあと再度 `issues` 系で起動 | **冪等**（再作成せず「既に存在」系コメント） | **合格** | Issue #11 コメント: 「対応ブランチは既に存在します。」＋同一 Branch 名 |
| TC-ISS-04 | 同一 Issue に対する**短時間の複数 Run** | 同一タイムスタンプ付近で 2 Run | いずれも **ジョブ成功**（`concurrency` は cancel しない設定） | **合格** | Run `25206448046` / `25206448058` とも `event: issues`, `conclusion: success` |
| TC-ISS-05 | ワークフロー全体 | 上記 Run | `create-branch` ジョブ **success** | **合格** | 例: Run `25206448058` — Job `create-branch` conclusion `success` |

### 2.1 参照 URL（代表）

- Run（`issues` / success）: https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/25206448058  
- 同一 Issue ほぼ同時のもう 1 本: https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/25206448046  
- 直前時刻帯の別 Run（同ワークフロー・`issues`）: https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/25206412592  

### 2.2 GraphQL 確認メモ（Development / linked branch）

Issue #11 の `linkedBranches`（検証時点）:

- `ref.name`: `test/task-11-branch-auto-creation-workflow-validation`
- `target.oid`: `8ef4009e5ff2dee3036208356249b800c3a18dd5`（リポジトリ状態に依存するため再検証時は変わり得る）

---

## 3. 未実施・別紙で扱う項目（任意の追試験）

以下は今回の 1 Issue の実走ログからは**個別に切り分けていない**ため、必要に応じて別 Issue で追記するとよい。

| ID | 内容 |
|----|------|
| TC-ISS-OPT-01 | `issues.edited`（タイトル変更）による **リネーム（方針A）** の end-to-end |
| TC-ISS-OPT-02 | `no-branch` 付与時の **スキップ**（コメントなし／ログのみの仕様はワークフロー実装に従う） |
| TC-ISS-OPT-03 | `issues.unlabeled` による再計算・リネーム境界 |

---

## 4. 総合判定

**`issues` イベントによる自動実行は、必須ラベル不足・初回作成・冪等・複数 Run のいずれも期待どおり動作している**と判断できる（上記 Run URL および Issue #11 のコメント・linked branch で確認）。

---

## 5. 再検証コマンド例（メンテ用）

```bash
gh run list --workflow="Create branch from issue" --limit 15 --json databaseId,conclusion,event,displayTitle,url
gh run view <RUN_ID> --json conclusion,event,url,jobs
gh api repos/<owner>/<repo>/issues/11/comments --jq '.[].body'
```

GraphQL（linked branch）:

```bash
gh api graphql -f query='
query($owner:String!,$name:String!,$num:Int!){
  repository(owner:$owner,name:$name){
    issue(number:$num){ linkedBranches(first:5){ nodes{ ref { name target { oid } } } } }
  }
}' -F owner=<owner> -F name=<repo> -F num=11
```
