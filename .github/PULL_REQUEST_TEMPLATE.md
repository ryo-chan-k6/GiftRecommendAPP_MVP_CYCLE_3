## PR Template選択ガイド

このPR本文は種別別テンプレート未指定時の案内用です。PR種別に応じて、以下いずれかのテンプレートを使用してください。

| PR種別 | GitHub PR Template | Issue参照 | PR target |
| ------ | ------------------ | --------- | --------- |
| Task PR | `.github/PULL_REQUEST_TEMPLATE/task-pr.md` | `Related to #<Task Issue番号>` | Parent Epic Branch |
| Contract Task PR | `.github/PULL_REQUEST_TEMPLATE/contract-pr.md` | `Related to #<Task Issue番号>` | Parent Epic Branch |
| Epic PR | `.github/PULL_REQUEST_TEMPLATE/epic-pr.md` | `Closes #<Epic Issue番号>` | `develop` |

GitHub UIで手動作成する場合は、PR作成URLに `template=task-pr.md` / `template=contract-pr.md` / `template=epic-pr.md` を指定してください。

```text
?template=task-pr.md
?template=contract-pr.md
?template=epic-pr.md
```

GitHub CLIで作成する場合は、対象PR種別に対応するテンプレートを明示してください。

```bash
gh pr create --template .github/PULL_REQUEST_TEMPLATE/task-pr.md
gh pr create --template .github/PULL_REQUEST_TEMPLATE/contract-pr.md
gh pr create --template .github/PULL_REQUEST_TEMPLATE/epic-pr.md
```

AI主導PR作成では、`prompts/templates/pr/` 配下のPrompt PR Templateを正本としてPR本文を生成します。

PR本文には `/review-pr` などの次Actionコマンドを記載しません。次ActionはCommand実行手順またはレビュー依頼コメントで扱います。
