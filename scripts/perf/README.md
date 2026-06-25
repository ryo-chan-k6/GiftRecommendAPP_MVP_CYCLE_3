# scripts/perf/

Reco 性能フィジビリティ PoC（Epic #759 / TV-007）向けの計測ハーネス。

正本: [Reco性能フィジビリティ検証計画書](../../docs/90_PoC/性能フィジビリティ/Reco性能フィジビリティ検証計画書.md)

## ファイル

| ファイル | 役割 |
| -------- | ---- |
| `reco_pipeline_bench.py` | パイプライン計測 CLI |
| `output/` | ローカル実行時の JSON / Markdown 出力（Git 管理外） |

## モード

| モード | Phase | 説明 |
| ------ | ----- | ---- |
| `skeleton` | Phase1 | Phase4a scaffold パイプライン（`apps/reco` **変更なし**）の wall-clock 実測 |
| `live` | Phase2 | **予約**。Epic #260 完了後の `poc-live-verification` Task で実装・有効化 |

### live モード拡張点（Phase2）

Phase2 では以下を `reco_pipeline_bench.py` に追加する想定（本 Task の scope 外）。

- `--mode live` で Orchestrator 経由の実パイプライン実行
- ephemeral DB / seed 起動前提の接続オプション
- OpenAI mock / secrets 切替（`test-reco-quality.yml` と同型）
- フェーズ別計測を MOD-RECO-001 実モジュール境界に合わせて更新

## 前提

- `apps/reco` の Python 環境（uv）
- `apps/reco` を変更しない（skeleton は既存 `PipelineRunner` + scaffold steps を利用）

## local 実行（skeleton）

専用 worktree（Issue #762）で作業すること（`1 Issue = 1 worktree`）。

```bash
# 作業開始前確認
pwd
git branch --show-current   # spike/task-762-reco-perf-harness
git worktree list

# reco venv 準備（初回のみ）
./scripts/dev/setup-python-reco.sh

# 計測（リポジトリ root から）
cd apps/reco
uv run python ../../scripts/perf/reco_pipeline_bench.py \
  --mode skeleton \
  --iterations 50 \
  --output-dir ../../scripts/perf/output
```

出力:

- `scripts/perf/output/report.json` — フェーズ別 p50/p95、計測ポイント ID、暫定上限との比較用メタデータ
- `scripts/perf/output/summary.md` — 人間 / Agent 可読サマリ

## GHA Layer2 実行

通常 PR CI（`ci.yml`）とは分離。`workflow_dispatch` のみ。

```bash
gh workflow run perf-feasibility-reco.yml \
  -f pipeline_mode=skeleton \
  -f iterations=50
```

実行後、artifact `reco-perf-bench-<run_id>` と job summary を確認する。

## 計測ポイント

検証計画書 §6 に準拠。主対象は **入力解析〜 Ranking**（`reason` は参考）。

| scaffold step | measurement_point | 備考 |
| ------------- | ----------------- | ---- |
| `input_parse` | `input_parse` | §6.1 / `phase_config` 近似 |
| `user_feature` | `user_meaning` | `phase_user_meaning` |
| `retrieval` | `retrieval` | `phase_retrieval` |
| `matching` | `matching` | `phase_matching` |
| `ranking` | `ranking` | `phase_ranking` |
| `reason` | `reason` | 参考（TV-007 主対象外） |

暫定上限（MOD-RECO-001 §13.2）: 全体 soft 2,000ms / hard 4,000ms。詳細は計画書 §7。

## 関連 Issue / Branch

| 項目 | 値 |
| ---- | --- |
| Epic | #759 |
| Task | #762 |
| Branch | `spike/task-762-reco-perf-harness` |
| PR target | `spike/epic-759-reco-performance-feasibility-poc` |
