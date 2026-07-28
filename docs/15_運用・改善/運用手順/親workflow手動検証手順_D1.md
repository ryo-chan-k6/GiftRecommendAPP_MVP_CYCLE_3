# 親workflow 手動検証手順（D1）

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 対象 Epic | [#1637](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1637) |
| 方針 | Human 確定: **案 A**（schedule 無効維持）/ **D1**（低 `max_items` の `workflow_dispatch`） |
| 正本 | [バッチ親workflow_schedule有効化ギャップ一覧](../../05_アプリケーション設計/アプリ/batch/バッチ親workflow_schedule有効化ギャップ一覧.md) §7・§8 |
| 作成日 | 2026-07-28 |

### 1.1 目的

親 workflow を定期 schedule なしで手動起動し、jobs.needs 連鎖とシークレット継承が動くことを確認する。

### 1.2 やらないこと

| 禁止 | 理由 |
| ---- | ---- |
| `on.schedule` コメント解除 | 案 A |
| `dry_run` input 追加 | D2 不採用 |
| secret / token / `.env` 実値の記録 | security |
| production 無承認の定期開始 | Epic out_of_scope |

---

## 2. 前提

- リポジトリに親 YAML が存在する（E1）
- GitHub Actions の必要な Secrets / Variables が設定済み（値は本手順に書かない）
- 実行者は `workflow_dispatch` 権限を持つ（例: machine account）

---

## 3. 検証対象

| 優先 | Workflow | ファイル | 推奨 input |
| ---- | -------- | -------- | ---------- |
| **必須** | Batch Daily Orchestrator | `batch-daily-orchestrator.yml` | `max_items=1`（または十分小さい値）、`run_retry_after=false` |
| 任意 | Batch Weekly Orchestrator | `batch-weekly-orchestrator.yml` | `max_items=1`、`run_offline_evaluation=false` |
| 任意 | Batch Manual Orchestrator | `batch-manual-orchestrator.yml` | 短い `scenario` のみ。本線検証の代替にはしない |

Wave 1 の完了条件は **daily 必須**。weekly / manual は時間・コスト次第でスキップ可（結果に理由を書く）。

---

## 4. 手順（daily・D1）

### 4.1 起動

```bash
# Machine account 認証後
gh workflow run "Batch Daily Orchestrator" \
  --repo ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3 \
  --ref develop \
  -f max_items=1 \
  -f run_retry_after=false
```

UI から起動する場合: Actions → Batch Daily Orchestrator → Run workflow。  
`--ref` は通常 `develop`（親 YAML がマージ済みの既定ブランチ）。

### 4.2 監視

```bash
gh run list --workflow=batch-daily-orchestrator.yml --limit 3
gh run view <run_id> --json status,conclusion,url,jobs
```

確認観点（secret なし）:

| 観点 | 期待 |
| ---- | ---- |
| 親 run が queued → in_progress → completed | ハングしない |
| `ranking_snapshot` → `item_import` → `item_meaning_generation` → `distribution_metrics` | needs 順で起動 |
| `retry_failed_items` | `run_retry_after=false` ならスキップ |
| 失敗時 | どの job 名で失敗したかを結果 docs に記録（ログ本文・secret は貼らない） |

### 4.3 記録

結果は [親workflow手動検証結果（D1）](./親workflow手動検証結果_D1.md) に追記する。

含めてよいもの: run URL、日時、input 名と**非機密**値（`max_items` 等）、conclusion、失敗 job 名、所見。  
含めてはいけないもの: secret、token、Authorization、接続文字列実値、個人情報。

---

## 5. 合格判定

| 判定 | 条件 |
| ---- | ---- |
| **PASS** | daily 親 run が completed かつ結論が success（または意図したスキップのみ） |
| **PARTIAL** | 連鎖の一部まで成功し、後段が環境依存で失敗。原因と次アクションを結果に記載 |
| **FAIL** | 親が起動できない、または needs 連鎖が設計どおり動かない |
| **SKIP** | 権限・Secrets 未整備等で起動不可。理由を結果に記載 |

案 A のため、PASS でも **schedule は有効化しない**。案 B への移行は検証結果を見た Human 再判断。

---

## 6. 関連

| 文書 | 役割 |
| ---- | ---- |
| [バッチ実行スケジュール設計書](../../05_アプリケーション設計/アプリ/batch/バッチ実行スケジュール設計書.md) §16.1 | Phase1 手動中心 |
| [バッチ親workflow_schedule有効化ギャップ一覧](../../05_アプリケーション設計/アプリ/batch/バッチ親workflow_schedule有効化ギャップ一覧.md) | #1637 正本 |
