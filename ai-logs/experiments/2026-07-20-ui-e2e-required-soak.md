# Experiment: UI E2E required 昇格前 soak 進捗トラッキング

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-20 |
| Epic | #1483 |
| 関連 | #1471（gate / 方針正本） / #1464（UI E2E 導入） / #1476（Node 24 復帰） |
| 目的 | required 昇格前の soak（2週間 かつ 10 PR・flake 0）を追いやすくする |

## 1. 基準（正本）

判断の正本は次とする。

- `ai-logs/human-decisions/2026-07-20-ui-e2e-required-promotion-plan.md`
- 基準: **2 週間 かつ 10 PR で flake 0**
- required 対象想定チェック名: **`UI E2E gate`**
- 対象ブランチ: **develop**

### 1.1 soak 開始日（推奨）

| 項目 | 値 |
| ---- | ---- |
| since | `2026-07-19T16:37:25Z` |
| 根拠 | PR #1472 merge（`ui-e2e-gate` 導入） |
| 注記 | PR #1478（Node 24 / Playwright 1.61.1）は soak 途中の環境変化。必要なら Human が since を #1478 merge に繰り下げてよい |

### 1.2 カウント定義（本トラッキング）

| 項目 | 定義 |
| ---- | ---- |
| カウント対象 PR | heavy job **`UI E2E (S1)` が success / failure / timed_out で終了した** PR（`skipped` / `cancelled` は除外） |
| flake（簡易） | soak 期間内に、cancelled 文脈でなく decide=success のうえでの `UI E2E (S1)` / `UI E2E gate` の `failure` / `timed_out` |
| cancelled 文脈 | run conclusion / Decide / S1 のいずれかが `cancelled`（concurrency cancel-in-progress 等）。**flake に含めない** |
| decide 失敗 | Decide ジョブ自体が failure（API rate limit 等）のときの gate failure は **flake に含めない**（判定不能・インフラ） |
| nightly | `schedule` 実行は安定性監視として記録するが、**10 PR カウントには含めない** |
| 自動昇格 | **しない**（判定ヒントのみ。required 設定は Human） |

### 1.3 Human 確認事項（観測定義）

| 項目 | 内容 |
| ---- | ---- |
| decide 失敗の扱い | 現状実装では decide failure（rate limit 等）に伴う gate failure を flake から除外する。より厳しく「decide failure も flake」とする場合は Human 判断後に定義・実装を更新する |

## 2. 使い方

```bash
# テキスト要約
./scripts/ops/summarize-ui-e2e-soak.sh

# Markdown（本ログへの貼り付け用）
./scripts/ops/summarize-ui-e2e-soak.sh --markdown

# since を Node 24 復帰に繰り下げる場合の例
./scripts/ops/summarize-ui-e2e-soak.sh --since 2026-07-20T14:23:41Z --markdown
```

必要: `gh` CLI（repo 読み取り） / `python3`。

運用: 週 1 回程度、または主導線 PR がまとまって増えたタイミングで再集計し、下記スナップショットを追記する。

## 3. 初回スナップショット（事実）

以下は `./scripts/ops/summarize-ui-e2e-soak.sh --markdown` の出力を転記したものである（2026-07-20T14:38:31Z）。

| 項目 | 値 |
| ---- | ---- |
| 集計日時 (UTC) | 2026-07-20T14:38:31Z |
| since | `2026-07-19T16:37:25Z` |
| 経過日数 | 0.9 / 目標 14 |
| 残日数目安 | 13.1 |
| 総 run 数 | 7 |
| schedule | 1 |
| pull_request | 6 |
| workflow_dispatch | 0 |
| S1 実行 run | 2（success=2 / fail=0 / cancelled=0） |
| gate fail run | 0 |
| S1 実行ユニーク PR 数 | 1 / 10 |
| PR 一覧 | `[1478]` |
| flake（簡易） | false |
| 判定ヒント | IN PROGRESS (need days>=14 and PRs>=10 and flake=0) |

## 4. 進捗メモ

| 日付 (UTC) | 経過日 | S1 PR 数 | flake | メモ |
| ---------- | -----: | -------: | ----- | ---- |
| 2026-07-20 | 0.9 | 1/10 | false | 初回。#1478 のみ S1 実行。nightly 1 回 success。主導線外 PR は gate-only pass |

## 5. Human 判断への引き渡し

soak 完了条件を満たしたら（スクリプトが `READY FOR HUMAN required-promotion review` を出すか、同等の材料が揃ったら）:

1. 本ログの最新スナップショットを確認する
2. develop の branch protection に **`UI E2E gate`** を required 追加するか判断する
3. 結果を `ai-logs/human-decisions/2026-07-20-ui-e2e-required-promotion-plan.md` の状態欄へ反映する
