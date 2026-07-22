# 外部AI API疎通検証計画（TV-005・最小）

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 検証ID | TV-005 |
| 文書種別 | PoC 検証計画（最小） |
| 方針正本 | [TV-005_外部AI_API疎通](../計画/TV要件・実施方針/TV-005_外部AI_API疎通.md) |
| 関連 Epic / Task | [#1565](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1565) / [#1566](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1566) |
| 結果 | [外部AI_API疎通検証結果](./外部AI_API疎通検証結果.md) |

---

## 2. 目的と切り分け

| 項目 | 内容 |
| ---- | ---- |
| 目的 | Embedding / LLM の**専用**疎通・応答時間・失敗形式・トークン/コスト概算を確認する |
| TV-007 との差 | TV-007 は Reco E2E（Orchestrator）内の OpenAI 寄与。本 TV はパイプライン外の API 単体計測 |
| out of scope | TV-006、TV-007 再実施、`apps/**` 改修、大量課金、rate limit 大量誘発、正式 Error/Reco/Batch docs 独断更新 |

---

## 3. 計測設計

| 項目 | 方針 |
| ---- | ---- |
| ハーネス | `scripts/perf/openai_connectivity_bench.py` |
| クライアント系統 | `openai_bench_clients.py` と同系統の HTTP（本スクリプトは apps/reco 非依存） |
| モデル | Embedding `text-embedding-3-small` / Chat `gpt-4o-mini` |
| モード | `mock`（HTTP 非実行）と `secrets`（`OPENAI_API_KEY` 実疎通）を区別 |
| 件数 | mock 20 回程度 / secrets 10 回程度（warmup 可）。大量実行は Human 承認後 |
| 指標 | wall-clock min / avg / p50 / p95 / max、token、料金概算（公開単価×token） |
| 失敗形式 | mock で 401 / 429 / timeout を再現。secrets は invalid model による 4xx を 1 回のみ |
| rate limit | 本 Phase では軽量観測のみ。意図的な大量誘発はしない |
| secret | env / GitHub Secrets のみ。成果物・ログに実値を書かない |

### 3.1 実行コマンド（local）

```bash
# mock
cd apps/reco
uv run python ../../scripts/perf/openai_connectivity_bench.py \
  --mode mock --iterations 20 --probe-failures \
  --output-dir ../../scripts/perf/output-tv005-mock

# secrets（値は echo しない）
set -a && source .env && set +a
cd apps/reco
uv run python ../../scripts/perf/openai_connectivity_bench.py \
  --mode secrets --iterations 10 --warmup 1 --probe-failures \
  --output-dir ../../scripts/perf/output-tv005-secrets
```

出力（Git 管理外）: `report.json` / `summary.md`

---

## 4. 判定枠（本 TV）

| ラベル | 意味（TV-005） |
| ------ | -------------- |
| Go | 疎通成功、失敗形式を説明可能、コストが PoC 規模で問題なし、致命制約なし |
| Adjust | 疎通は可能だが、timeout / retry / コスト設計の調整が必要 |
| Block | 疎通不能、または成立を妨げる制約（認証・料金・仕様）がある |

Reco 全体 SLO（内部 1.5s/2s・同期外部 AI 込み 6s/8s）の最終判定は TV-007 / 正式 docs 側。本 TV は API 単体の根拠を提供する。

---

## 5. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-22 | 初版（#1566） |
