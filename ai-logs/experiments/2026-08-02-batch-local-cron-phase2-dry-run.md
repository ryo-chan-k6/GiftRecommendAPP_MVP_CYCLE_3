# Experiment: batch-local-cron-phase2 dry-run

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-08-02-batch-local-cron-phase2-dry-run` |
| Log種別 | `experiment` |
| 関連Issue | #1824 |
| 親Epic | #1818 |
| 目的 | Phase2 親シェルの `--dry-run`（Phase1 互換スキップ / `--run-meaning`）を再現記録する |
| 実行環境 | Task worktree（WSL local）。live なし |
| 日時 | 2026-08-02 |

**注意:** secret / token / 接続文字列 / egress IP 実値は記録しない。
正本の運用記録は [local_cron_Phase2_dry-run検証結果](../../docs/15_運用・改善/運用手順/local_cron_Phase2_dry-run検証結果.md) とする。本ファイルは experiments 補助ログ。

---

## 2. 実行コマンド（事実）

```bash
./scripts/batch/local_daily_orchestrator.sh --dry-run
./scripts/batch/local_daily_orchestrator.sh --dry-run --run-meaning
./scripts/batch/local_weekly_orchestrator.sh --dry-run
./scripts/batch/local_weekly_orchestrator.sh --dry-run --run-meaning
```

---

## 3. 結果（事実）

| コマンド | exit | `run_meaning` | 備考 |
| -------- | ---: | ------------: | ---- |
| daily `--dry-run` | 0 | 0 | meaning / distribution_metrics skip |
| daily `--dry-run --run-meaning` | 0 | 1 | 009〜016 STEP ok |
| weekly `--dry-run` | 0 | 0 | meaning / distribution_metrics skip |
| weekly `--dry-run --run-meaning` | 0 | 1 | existing 後に 009〜016 STEP ok |

- `--live-rakuten` 未実行
- 実 crontab 未変更
- ログに secret 実値なし

---

## 4. Human 判断への引き渡し

- cron-cutover（実 crontab へ `--run-meaning` 追加等）は **Human ゲート**
- 着手条件: Phase1 観測完了 **または** Human 明示承認
- 本実験は dry-run 材料のみ。載せ替え実施・#1811 完了操作は含まない
