# scripts/perf/

Reco 性能フィジビリティ PoC（TV-007）および外部 AI API 疎通 PoC（TV-005）向けの計測ハーネス。

正本:

- TV-007: [Reco性能フィジビリティ検証計画書](../../docs/90_PoC/性能フィジビリティ/Reco性能フィジビリティ検証計画書.md)
- TV-005: [外部AI_API疎通検証計画](../../docs/90_PoC/外部API疎通検証/外部AI_API疎通検証計画.md)

## ファイル

| ファイル | 役割 |
| -------- | ---- |
| `reco_pipeline_bench.py` | パイプライン計測 CLI（skeleton / live）※ TV-007 |
| `openai_bench_clients.py` | live + secrets 用 OpenAI HTTP クライアント（bench 専用・apps/reco 非改修） |
| `openai_connectivity_bench.py` | Embedding / LLM **専用**疎通計測 CLI（TV-005。Reco E2E 非依存） |
| `output/` / `output-*/` | ローカル実行時の JSON / Markdown 出力（Git 管理外） |

## モード

| モード | Phase | 説明 |
| ------ | ----- | ---- |
| `skeleton` | Phase1 | Phase4a scaffold パイプライン（`apps/reco` **変更なし**）の wall-clock 実測 |
| `live` | Phase2/3 | `RecommendationOrchestrator` + `CompositionMode.PRODUCTION`。ephemeral DB + seed 前提 |

### live モード

| 項目 | 内容 |
| ---- | ---- |
| 実行経路 | Python 直接（HTTP 経由ではない） |
| DB | `DATABASE_URL` 必須。手順は [scripts/db/README.md](../db/README.md)（`test-reco-quality.yml` 同型） |
| OpenAI | `--openai-mode mock`（scaffold Embedding/LLM）/ `secrets`（`OPENAI_API_KEY` 実疎通） |
| 計測 | Orchestrator `phase_log_events` の duration を TV-007 step に合算 + 外側 wall-clock |
| hard timeout | 既定は計測のため bypass（`--enforce-hard-timeout` で本番相当 hard を有効化） |
| 代表入力 | `friend_casual` × `birthday`（`--relationship-code` / `--occasion-code` で変更可） |
| Phase3 主対象 | **Reason 込み E2E**（input_parse → reason）。Ranking までは比較指標 |

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

- `report.json` — Ranking まで / Reason 込み / phase_output の p50/p95、分離 Go/Adjust/Block、openai_mode メタ
- `summary.md` — 人間 / Agent 可読サマリ

## GHA Layer2 実行

通常 PR CI（`ci.yml`）とは分離。`workflow_dispatch`。

**注意:** 同一 Branch の concurrency により、mock と secrets を同時 dispatch すると後勝ちで cancel される。逐次実行すること。

```bash
# live + mock
gh workflow run perf-feasibility-reco.yml \
  --ref spike/task-1536-reco-perf-phase3-reason-e2e \
  -f pipeline_mode=live \
  -f openai_mode=mock \
  -f iterations=20 \
  -f warmup=2

# live + OpenAI secrets（上記完了後）
gh workflow run perf-feasibility-reco.yml \
  --ref spike/task-1536-reco-perf-phase3-reason-e2e \
  -f pipeline_mode=live \
  -f openai_mode=secrets \
  -f iterations=20 \
  -f warmup=2 \
  -f force_llm=true
```

実行後、artifact `reco-perf-bench-<run_id>` と job summary を確認する。

## 計測ポイント

検証計画書 §6 に準拠。

| Phase | 主対象 |
| ----- | ------ |
| Phase1/2 | 入力解析〜 Ranking（`reason` は参考） |
| **Phase3** | **入力解析〜 Reason**（Ranking までは比較） |

| TV-007 step | measurement_point | live Orchestrator 集約 phase（合算） |
| ----------- | ----------------- | ------------------------------------ |
| `input_parse` | `input_parse` | `request_received` + `config_resolved` |
| `user_feature` | `user_meaning` | `semantic_extracted` 〜 `query_embedding_generated` |
| `retrieval` | `retrieval` | `pre_hard_filter` / `retrieval` / `post_hard_filter` |
| `matching` | `matching` | `matching_completed` |
| `ranking` | `ranking` | `ranking_completed` |
| `reason` | `reason` / `phase_output` | `result_generated` + `reason_generated`（**`response_built` 除外**・#1545） |
| `response_built` | （診断専用） | `response_built` のみ。累積壁時計のため `phase_output` に含めない |

### phase_output 計測定義（#1545）

| 定義 | 含む phase | 用途 |
| ---- | ---------- | ---- |
| **現行（#1545 以降）** | `result_generated` + `reason_generated` | Reason / Output 寄与の監視 |
| 旧（Phase3 初版〜#1545 前） | 上記 + `response_built`（累積壁時計） | 合算値が Reason 単体と乖離するため廃止 |
| Reason 込み E2E | 外側 wall-clock（`pipeline_total_ms`） | soft 6s / hard 8s の主判定。計測定義変更の対象外 |

判定枠（#1533）: Reco 内部 soft/hard **1.5s/2s**、同期外部 AI 込み **6s/8s**。`phase_output` 案 A（soft 3s / hard 7s）は Human Review（#1539）。詳細は計画書 §7・設計反映メモ。

## TV-005（外部 AI API 疎通）

Reco パイプラインとは分離し、Embedding / Chat Completions の応答時間・失敗形式・トークン/コスト概算を計測する。

| 項目 | 内容 |
| ---- | ---- |
| スクリプト | `openai_connectivity_bench.py` |
| モード | `mock`（HTTP 非実行） / `secrets`（`OPENAI_API_KEY`） |
| 推奨モデル | `text-embedding-3-small` / `gpt-4o-mini` |
| 結果 doc | [外部AI_API疎通検証結果](../../docs/90_PoC/外部API疎通検証/外部AI_API疎通検証結果.md) |

```bash
cd apps/reco
uv run python ../../scripts/perf/openai_connectivity_bench.py \
  --mode mock --iterations 20 --probe-failures \
  --output-dir ../../scripts/perf/output-tv005-mock

# secrets（値は echo しない）
set -a && source ../../.env && set +a
uv run python ../../scripts/perf/openai_connectivity_bench.py \
  --mode secrets --iterations 10 --warmup 1 --probe-failures \
  --output-dir ../../scripts/perf/output-tv005-secrets
```

## 関連 Issue / Branch

| 項目 | 値 |
| ---- | --- |
| Phase2 Epic / Task | #1512 / #1513 |
| Phase3 Epic / Task | #1535 / #1536 |
| phase_output 計測定義修正 | #1544 / #1545 |
| TV-005 Epic / Task | #1565 / #1566 |
| Branch（TV-005 Task） | `spike/task-1566-tv-005-connectivity-verification` |
| PR target（TV-005） | `spike/epic-1565-tv-005-external-ai-api-connectivity` |
