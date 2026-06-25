# Reco性能フィジビリティ検証結果 Phase1

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | PoC 検証結果（Phase1） |
| 検証ID | TV-007 |
| 検証モード | `skeleton` 実測 + `analysis` 試算 |
| 関連 Epic | [#759](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/759) |
| 関連 Task | [#763](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/763) poc-report |
| 計画書 | [Reco性能フィジビリティ検証計画書](./Reco性能フィジビリティ検証計画書.md) |
| 計測日 | 2026-06-25（JST） |

**注意:** Phase1 の skeleton 実測は **Phase4a scaffold**（ドメイン処理なし）の下限参考値である。§13.2 暫定値の**最終判定は Phase2 live 実測後**とする（計画書 §7.3）。

---

## 2. 実施概要

| 項目 | 内容 |
| ---- | ---- |
| ハーネス | `scripts/perf/reco_pipeline_bench.py` |
| モード | `skeleton` |
| 対象範囲 | 入力解析〜 Ranking（`reason` は参考） |
| local 実行 | iterations=100, warmup=5 |
| GHA 実行 | `perf-feasibility-reco.yml`（Epic Branch） |
| apps/reco 変更 | なし |

### 2.1 実行コマンド（local）

```bash
cd apps/reco
uv run python ../../scripts/perf/reco_pipeline_bench.py \
  --mode skeleton \
  --iterations 100 \
  --warmup 5 \
  --output-dir ../../scripts/perf/output-phase1-report
```

### 2.2 GHA 実行記録

| Run ID | トリガ | iterations | 結果 | URL |
| ------ | ------ | ---------- | ---- | --- |
| 28147486256 | push | 50 | success | [Actions](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/28147486256) |
| 28147511559 | workflow_dispatch | 10 | success | [Actions](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/28147511559) |

artifact: `reco-perf-bench-<run_id>`（`report.json`, `summary.md`）

---

## 3. skeleton 実測結果

### 3.1 TV-007 パイプライン全体（input_parse → ranking）

| 環境 | iterations | p50 (ms) | p95 (ms) | max (ms) |
| ---- | ---------- | -------- | -------- | -------- |
| local（WSL2） | 100 | 0.001 | 0.001 | 0.001 |
| GHA（ubuntu-latest） | 50 | 0.001 | 0.001 | 0.001 |

**解釈（事実）:** scaffold ステップは空処理に近く、sub-ms 台で完走する。

**解釈（推論）:** 本値は **計測ハーネス・パイプライン配線の動作確認**には有効だが、Reco 本処理（DB / pgvector / Embedding / Matching 計算）の性能見込みを表さない。

### 3.2 フェーズ別実測（local, p95）

| scaffold step | measurement_point | p95 (ms) | §13.2 hard 上限 (ms) | skeleton との比較 |
| ------------- | ----------------- | -------- | -------------------- | ----------------- |
| input_parse | input_parse | 0.0001 | 300（phase_config 近似） | 上限内（参考のみ） |
| user_feature | user_meaning | 0.0001 | 1,000 | 上限内（参考のみ） |
| retrieval | retrieval | 0.0001 | 1,000 | 上限内（参考のみ） |
| matching | matching | 0.0001 | 500 | 上限内（参考のみ） |
| ranking | ranking | 0.0001 | 1,000 | 上限内（参考のみ） |
| reason（参考） | reason | 0.0001 | — | TV-007 主対象外 |

### 3.3 ハーネス検証の結論

| 観点 | Phase1 結果 |
| ---- | ----------- |
| bench 完走 | local / GHA ともに success |
| 出力形式 | JSON / Markdown / artifact 生成を確認 |
| 計測ポイント ID | 計画書 §6 と整合 |

---

## 4. 設計値・試算（analysis）

skeleton 実測が本処理を含まないため、**性能要件 §4.1** および **テスト定義書 §9.1.4** に基づく試算で Phase1 見込みを補完する。

### 4.1 性能要件 §4.1 ステップ目標との対照

| ステップ | 設計目標 (ms) | Phase1 skeleton p95 | 差分の意味 |
| -------- | ------------- | --------------------- | ---------- |
| 入力解析 | 50 | ≪1 | skeleton は未計測。live で Config 解決込み要計測 |
| Meaning 推定 | 300 | ≪1 | Embedding / LLM 依存。Phase2 要計測 |
| Retrieval | 300 | ≪1 | pgvector・件数スケール依存。**リスク集中** |
| Matching | （内訳未分離） | ≪1 | 候補数比例。Phase2 要計測 |
| Ranking | 300 | ≪1 | top_k / MMR。Phase2 要計測 |
| **合計目標** | **≈1,000** | ≪1 | 設計上は soft 2,000ms 内に収まる**見込み** |

### 4.2 §9.1.4 観点別見込み（試算・推論）

| §9.1.4 観点 | Phase1 見込み | 根拠 | Phase2 要否 |
| ----------- | ------------- | ---- | ----------- |
| Reco 全体（2 秒台） | **成立見込みあり（要 live 確認）** | 設計内訳合計 ≈1,000ms + バッファ ≈1,000ms が soft 2,000ms 内 | **必須** |
| User Feature 生成 | 数百 ms 以内を目標 | §4.1 Meaning 300ms。外部 AI 遅延が変動要因 | **必須** |
| Candidate Retrieval | **要重点確認** | pgvector・候補件数がボトルネック候補 | **必須** |
| Matching | 候補数に比例 | 設計上 Ranking 前段。件数別計測要 | **必須** |
| Ranking / MMR | top_k 依存 | 急増なし想定だが未実測 | **必須** |
| Embedding / 外部 AI | rate limit・latency 変動 | mock / secrets 両系統で Phase2 計測 | **必須** |
| DB 検索 | Phase1 対象外 | index 効果は live + seed 前提 | **必須** |

### 4.3 §13.2 暫定値との距離（試算）

| 種別 | 暫定値 | 試算ベース見込み | skeleton 実測 |
| ---- | ------ | ---------------- | ------------- |
| soft（p95 目標） | 2,000ms | 設計合計 ≈1,000ms 前後 → **余裕あり（推論）** | 判定に不十分 |
| hard（中断） | 4,000ms | フェーズ別上限合計は全体 4,000ms 優先設計と整合 | 判定に不十分 |

---

## 5. 暫定判定（Human 判断材料）

**Phase1 時点の結論:** skeleton + 試算により **早期フィジビリティは「否定材料なし」** だが、**Go の最終確定は Phase2 live 実測後**とする。

| 対象 | 暫定判定候補 | 根拠区分 | コメント |
| ---- | ------------ | -------- | -------- |
| soft 2,000ms | **Go候補** | 推論（設計内訳試算） | live p95 で再評価 |
| hard 4,000ms | **Go候補** | 推論（設計・api timeout 整合） | live max/p95 で再評価 |
| フェーズ別 hard 上限 | **Phase2 確認待ち** | 未確認 | skeleton では未計測 |
| アーキテクチャ全体 | **Block 候補なし** | 推論 | Retrieval / AI が Phase2 焦点 |

| ラベル定義 | 本 Phase1 での適用 |
| ---------- | ------------------ |
| Go | 暫定値維持の見込み — **候補として記載、未確定** |
| Adjust | Phase1 では根拠不足のため未採用 |
| Block | Phase1 では根拠不足のため未採用 |

---

## 6. Phase2 への引き継ぎ

Phase2（Epic #260 完了後 / `poc-live-verification`）で以下を実施する。

1. `reco_pipeline_bench.py --mode live` の有効化
2. ephemeral DB + seed 上での p50/p95 実測
3. 候補件数・top_k を変えたスケール計測
4. §13.2 に対する **Go / Adjust / Block の実測根拠付き判定**
5. [設計反映メモ](./設計反映メモ.md) の Phase2 追記

詳細チェックリストは設計反映メモ §3 を正とする。

---

## 7. 未実施・残リスク

| 項目 | 内容 |
| ---- | ---- |
| live 実測 | Epic #260 完了待ち（Phase1 完了のブロッカーではない） |
| 候補件数スケール | Phase2 で実施 |
| OpenAI 実 API | Phase2（mock / secrets 比較） |
| MOD-RECO-001 正式更新 | Phase2 完了後の別 Task |

---

## 8. 変更履歴

| 日付 | 変更内容 | 関連 |
| ---- | -------- | ---- |
| 2026-06-25 | Phase1 結果初版（skeleton 実測 + 試算 + 暫定判定候補） | Issue #763 |
