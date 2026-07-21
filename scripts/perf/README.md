# scripts/perf/

Reco 性能フィジビリティ PoC（TV-007）向けの計測ハーネス。

正本: [Reco性能フィジビリティ検証計画書](../../docs/90_PoC/性能フィジビリティ/Reco性能フィジビリティ検証計画書.md)

## ファイル

| ファイル | 役割 |
| -------- | ---- |
| `reco_pipeline_bench.py` | パイプライン計測 CLI（skeleton / live） |
| `openai_bench_clients.py` | live + secrets 用 OpenAI HTTP クライアント（bench 専用・apps/reco 非改修） |
| `output/` | ローカル実行時の JSON / Markdown 出力（Git 管理外） |

## モード

| モード | Phase | 説明 |
| ------ | ----- | ---- |
| `skeleton` | Phase1 | Phase4a scaffold パイプライン（`apps/reco` **変更なし**）の wall-clock 実測 |
| `live` | Phase2 | `RecommendationOrchestrator` + `CompositionMode.PRODUCTION`。ephemeral DB + seed 前提 |

### live モード

| 項目 | 内容 |
| ---- | ---- |
| 実行経路 | Python 直接（HTTP 経由ではない） |
| DB | `DATABASE_URL` 必須。手順は [scripts/db/README.md](../db/README.md)（`test-reco-quality.yml` 同型） |
| OpenAI | `--openai-mode mock`（scaffold Embedding/LLM）/ `secrets`（`OPENAI_API_KEY` 実疎通） |
| 計測 | Orchestrator `phase_log_events` の duration を TV-007 step に合算 + 外側 wall-clock |
| hard timeout | 既定は計測のため bypass（`--enforce-hard-timeout` で本番相当 4,000ms を有効化） |
| 代表入力 | `friend_casual` × `birthday`（`--relationship-code` / `--occasion-code` で変更可） |

## 前提

- `apps/reco` の Python 環境（`./scripts/dev/setup-python-reco.sh`）
- live: ephemeral DB 起動済み + master / test-data seed
- live + secrets: `OPENAI_API_KEY`（実値は env / GitHub Secrets のみ。成果物へ非記載）

## local 実行

### skeleton

```bash
./scripts/dev/setup-python-reco.sh
cd apps/reco
uv run python ../../scripts/perf/reco_pipeline_bench.py \
  --mode skeleton \
  --iterations 50 \
  --output-dir ../../scripts/perf/output
```

### live（ephemeral DB）

```bash
# リポジトリ root
./scripts/db/start-local.sh
./scripts/db/migrate-up.sh
./scripts/db/seed-masters.sh
./scripts/db/seed-test-data.sh

# DATABASE_URL は supabase status の DB URL（.env に設定。実値は commit しない）
export DATABASE_URL  # 値はシェル上で設定。echo しない

cd apps/reco
uv run python ../../scripts/perf/reco_pipeline_bench.py \
  --mode live \
  --openai-mode secrets \
  --force-llm \
  --iterations 20 \
  --warmup 2 \
  --candidate-limit 100 \
  --top-k 5 \
  --output-dir ../../scripts/perf/output-live
```

出力:

- `report.json` — フェーズ別 p50/p95、Go/Adjust/Block 暫定判定、openai_mode メタ
- `summary.md` — 人間 / Agent 可読サマリ

## GHA Layer2 実行

通常 PR CI（`ci.yml`）とは分離。`workflow_dispatch`。

```bash
# skeleton
gh workflow run perf-feasibility-reco.yml \
  -f pipeline_mode=skeleton \
  -f iterations=50

# live + OpenAI secrets
gh workflow run perf-feasibility-reco.yml \
  --ref spike/task-1513-reco-perf-live \
  -f pipeline_mode=live \
  -f openai_mode=secrets \
  -f iterations=20 \
  -f warmup=2 \
  -f force_llm=true
```

実行後、artifact `reco-perf-bench-<run_id>` と job summary を確認する。

## 計測ポイント

検証計画書 §6 に準拠。主対象は **入力解析〜 Ranking**（`reason` は参考）。

| TV-007 step | measurement_point | live Orchestrator 集約 phase（合算） |
| ----------- | ----------------- | ------------------------------------ |
| `input_parse` | `input_parse` | `request_received` + `config_resolved` |
| `user_feature` | `user_meaning` | `semantic_extracted` 〜 `query_embedding_generated` |
| `retrieval` | `retrieval` | `pre_hard_filter` / `retrieval` / `post_hard_filter` |
| `matching` | `matching` | `matching_completed` |
| `ranking` | `ranking` | `ranking_completed` |
| `reason` | `reason` | `result_generated` + `reason_generated`（参考） |

暫定上限（MOD-RECO-001 §13.2）: 全体 soft 2,000ms / hard 4,000ms。詳細は計画書 §7。

## 関連 Issue / Branch

| 項目 | 値 |
| ---- | --- |
| Phase2 Epic | #1512 |
| Phase2 Task | #1513 |
| Branch | `spike/task-1513-reco-perf-live` |
| PR target | `spike/epic-1512-reco-performance-feasibility-poc-phase2` |
