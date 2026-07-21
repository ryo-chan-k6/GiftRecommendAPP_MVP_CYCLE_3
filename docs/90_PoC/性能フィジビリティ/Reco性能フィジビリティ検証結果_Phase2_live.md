# Reco性能フィジビリティ検証結果 Phase2 live

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | PoC 検証結果（Phase2 live） |
| 検証ID | TV-007 |
| 検証モード | `live`（ephemeral DB + OpenAI mock / secrets） |
| 関連 Epic | [#1512](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1512) |
| 関連 Task | [#1513](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1513) |
| 計画書 | [Reco性能フィジビリティ検証計画書](./Reco性能フィジビリティ検証計画書.md) |
| Phase1 結果 | [Reco性能フィジビリティ検証結果_Phase1](./Reco性能フィジビリティ検証結果_Phase1.md) |
| 計測日 | 2026-07-21（JST） |

**注意:** 本結果の Go / Adjust / Block は **実測根拠付きの暫定判定**である。§13.2 暫定値の最終採用は Human Review で確定する。正式 docs（性能要件 §5 / MOD-RECO-001 §13.2）更新は別 Task。

---

## 2. 実施概要

| 項目 | 内容 |
| ---- | ---- |
| ハーネス | `scripts/perf/reco_pipeline_bench.py --mode live` |
| 実行経路 | `RecommendationOrchestrator` + `CompositionMode.PRODUCTION`（HTTP 非経由） |
| OpenAI | `scripts/perf/openai_bench_clients.py` 差込（`apps/reco/src/**` 変更なし） |
| DB | GHA ephemeral Supabase + local Docker Supabase（同一 seed 手順） |
| 代表入力 | `friend_casual` × `birthday`、`top_k=5`、`candidate_limit=100` |
| hard timeout | 計測のため bypass（`--enforce-hard-timeout` 未使用）。壁時計は外側計測 |
| apps/reco 変更 | なし |

### 2.1 GHA 実行記録

| Run ID | モード | iterations | 結果 | URL |
| ------ | ------ | ---------- | ---- | --- |
| 29829674333 | live + secrets（`--force-llm`） | 20 | success | [Actions](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/29829674333) |
| 29830051761 | live + mock | 20 | success | [Actions](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/29830051761) |
| 29829993205 | skeleton（再現） | 50 | success | [Actions](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/29829993205) |

artifact: `reco-perf-bench-<run_id>`（`report.json`, `summary.md`）。secret 実値は成果物・ログに含まれていない。

### 2.2 local 実行（2026-07-21 再実施）

| 項目 | 状態 |
| ---- | ---- |
| Docker / Supabase | 起動確認済み（`scripts/db/start-local.sh`） |
| migrate / seed | 実施済み（`seed-masters` + `seed-test-data`、item=3） |
| local live + mock | **実施**（iterations=20, warmup=2）→ TV-007 p95≈696ms、**Go**、success=20/20 |
| local live + secrets | **実行試行したが実 API 未達** |
| secrets 未達理由 | ローカル `.env` の `OPENAI_API_KEY` がプレースホルダ（`your_openai_api_key_here`）。OpenAI は HTTP 401 `invalid_api_key`。全 20 iteration が `GRS-REC-004` で失敗 |
| secrets 正の計測 | GHA Secrets 注入の Run 29829674333 を正とする |

**事実:** local secrets 試行では embedding_calls=0 / llm_calls=22（Chat 401 で User Meaning 失敗）。ベンチは全失敗時に誤って Go とならないよう判定ロジックを修正済み（`all-fail→Block`）。

---

## 3. live 実測結果

### 3.1 TV-007 パイプライン全体（input_parse → ranking）

| 環境 | openai_mode | iterations | p50 (ms) | p95 (ms) | max (ms) | 暫定判定 |
| ---- | ----------- | ---------- | -------- | -------- | -------- | -------- |
| GHA | secrets | 20 | 2,247.5 | **4,529.3** | 6,720.0 | **Block**（p95 > hard 4,000） |
| GHA | mock | 20 | 411.5 | **451.3** | 475.0 | **Go**（p95 ≤ soft 2,000） |
| local（WSL2） | mock | 20 | 562.0 | **696.2** | 775.0 | **Go**（p95 ≤ soft 2,000） |
| local（WSL2） | secrets | 20 | — | — | — | **未成立**（API key プレースホルダ / 401。性能判定対象外） |
| GHA | skeleton（参考） | 50 | 0.001 | 0.001 | 0.001 | （Phase1 下限。判定不可） |

**事実:** GHA secrets 経路は OpenAI Embedding / Chat 実疎通あり（embedding_calls=22, llm_calls=22。warmup 含む）。mock 経路（GHA/local）は scaffold/in-memory（calls=0）で success=20/20。

### 3.1.1 GHA ↔ local 再現性（mock）

| 指標 | GHA mock | local mock | 差分（local − GHA） |
| ---- | -------- | ---------- | ------------------- |
| TV-007 p95 (ms) | 451.3 | 696.2 | +244.9 |
| user_meaning p95 (ms) | 226.6 | 360.5 | +133.9 |
| retrieval p95 (ms) | 93.7 | 126.1 | +32.4 |
| 判定 | Go | Go | 同一ラベル |

**解釈（推論）:** 絶対値は local（WSL2）の方が大きめだが、soft 2,000ms に対しては両環境とも余裕。再現性比較としては **判定ラベル一致**を確認できた。

### 3.2 フェーズ別実測（GHA, p95）

| TV-007 step | measurement_point | secrets p95 (ms) | mock p95 (ms) | §13.2 hard (ms) | 所見 |
| ----------- | ----------------- | ---------------- | ------------- | --------------- | ---- |
| input_parse | input_parse / phase_config | 121.0 | 132.1 | 300 | 両経路とも上限内 |
| user_feature | user_meaning / phase_user_meaning | **4,341.7** | 226.6 | 1,000 | secrets で大幅超過（OpenAI） |
| retrieval | retrieval / phase_retrieval | 73.5 | 93.7 | 1,000 | 上限内（seed 3 件前提） |
| matching | matching / phase_matching | 10.2 | 11.1 | 500 | 上限内 |
| ranking | ranking / phase_ranking | 9.4 | 10.1 | 1,000 | 上限内 |
| reason（参考） | reason / phase_output | 4,886.5 | 882.4 | 500 | TV-007 主対象外。参考として超過 |

### 3.2.1 フェーズ別実測（local mock, p95）

| TV-007 step | p95 (ms) | §13.2 hard (ms) |
| ----------- | -------- | --------------- |
| input_parse | 215.1 | 300 |
| user_feature | 360.5 | 1,000 |
| retrieval | 126.1 | 1,000 |
| matching | 19.1 | 500 |
| ranking | 20.1 | 1,000 |
| reason（参考） | 1,346.2 | 500 |

### 3.3 mock vs secrets 比較（User Meaning）

| openai_mode | user_meaning p95 (ms) | TV-007 p95 (ms) |
| ----------- | --------------------- | --------------- |
| mock | 226.6 | 451.3 |
| secrets | 4,341.7 | 4,529.3 |

**解釈（事実）:** 差分の主因は User Meaning 内の OpenAI 実疎通遅延である。Retrieval / Matching / Ranking は両経路で同程度かつ soft/hard に対して余裕がある。

---

## 4. §13.2 暫定値に対する判定

### 4.1 判定ルール（本 Task）

| 条件 | ラベル |
| ---- | ------ |
| TV-007 p95 ≤ soft 2,000ms | Go |
| soft < p95 ≤ hard 4,000ms | Adjust |
| p95 > hard 4,000ms | Block |

### 4.2 暫定判定（実測根拠付き）

| 計測系 | ラベル | 根拠 |
| ------ | ------ | ---- |
| live + secrets（GHA・主経路） | **Block** | TV-007 p95=4,529ms > hard 4,000ms。phase_user_meaning p95=4,342ms > 1,000ms |
| live + mock（GHA） | **Go** | TV-007 p95=451ms ≤ soft 2,000ms。主要フェーズ hard 内（reason 除く） |
| live + mock（local） | **Go** | TV-007 p95=696ms ≤ soft 2,000ms。GHA と判定一致 |

### 4.3 Human 向け整理（推論・未確定）

| 論点 | AI 推論 | Human 判断依頼 |
| ---- | ------- | -------------- |
| 最終ラベル | secrets 主経路なら Block。ただしボトルネックは OpenAI 外部遅延に集中し、Reco 内部（DB/pgvector/Matching/Ranking）は成立見込み | §13.2 を secrets 込みで維持するか、User Meaning の扱いを分けて Adjust とするか |
| soft/hard 維持 | 内部計算のみなら soft 維持の余地あり。secrets 込みの現状値では hard 超過 | 最終採用可否 |
| phase_user_meaning 1,000ms | secrets では非現実的。LLM 誘発・Embedding を含むなら上限見直し or 非同期化が候補 | フェーズ上限の調整方針 |
| phase_output 500ms | reason 参考計測でも mock で超過。TV-007 主対象外だが正式更新時に要検討 | Reason を主対象へ含めるか |

**推奨案（推論）:** 正式更新 Task では (1) Reco 内部（Retrieval〜Ranking）は Go 寄り、(2) User Meaning / Reason の外部 AI 遅延は Adjust（上限見直し・キャッシュ・非同期）として分離記載する。本 PoC の secrets 主経路ラベルはルールどおり **Block** を残す。

---

## 5. 設計反映メモ §3 チェックリスト消化

| 項目 | 状態 | 備考 |
| ---- | ---- | ---- |
| pipeline_total p50/p95/max（live） | 消化 | §3.1 |
| フェーズ別 p95 | 消化 | Orchestrator phase_log 合算 |
| TV-007 E2E wall-clock | 消化 | |
| GHA と local 再現性比較 | 消化 | mock: GHA/local とも Go（p95 451 vs 696）。secrets local は API key プレースホルダのため GHA を正 |
| Retrieval 件数別（100/500/1,000） | 未実施 | test-data seed は item **3 件**。件数スケールは追加 seed が必要 |
| Matching / Ranking top_k 別 | 部分 | top_k=5 / candidate_limit=100 の固定代表のみ |
| User Meaning mock vs secrets | 消化 | GHA で比較。local は mock のみ（secrets は key 待ち） |
| DB/pgvector index・件数スケール | 部分 | HNSW 付き seed 上で計測（GHA/local）。件数スケールは未実施 |
| Go/Adjust/Block | 消化 | §4 |
| Phase2 結果 doc | 消化 | 本文書 |
| 正式 docs 更新入力整理 | 消化 | §6 |
| `--mode live` 実装 | 消化 | |
| ephemeral DB 手順 README | 消化 | `scripts/perf/README.md` |
| artifact 読取 | 消化 | 本 Task で確認 |

---

## 6. 正式 docs 更新 Task への入力

| 対象 | Phase2 からの入力案 |
| ---- | ------------------- |
| MOD-RECO-001 §13.2 soft 2,000ms | mock 経路では成立。secrets 込みでは未達。Human が「外部 AI 込み / 内部のみ」を定義したうえで維持 or 調整 |
| hard 4,000ms | secrets 込み p95 が超過。api→reco timeout との整合は維持しつつ、User Meaning 分離 or hard 見直しを検討 |
| phase_user_meaning 1,000ms | secrets 実測と乖離大。調整候補 |
| phase_retrieval / matching / ranking | 現行暫定値で余裕（現行 seed 規模）。件数スケール後に再確認推奨 |
| 性能要件 §5 / §3.1 | Reco 内部は 2s 台見込みあり。外部 AI を同期含む場合は SLO 再定義が必要 |

---

## 7. 残リスク・未実施

| 項目 | 内容 |
| ---- | ---- |
| local secrets | `.env` の `OPENAI_API_KEY` がプレースホルダのため未達。実 key 設定後に再実行可能 |
| 件数スケール | seed 3 件のため 100/500/1,000 未実施 |
| hard timeout 有効時 | bypass 計測。本番 4s 中断時の部分完了挙動は別確認候補 |
| production 負荷 | out of scope |
| secret | 実値は成果物に含めない方針を遵守 |

---

## 8. 変更履歴

| 日付 | 変更内容 |
| ---- | -------- |
| 2026-07-21 | Phase2 live 初版（GHA secrets / mock / skeleton） |
| 2026-07-21 | local Docker 再計測（mock Go）。secrets は API key プレースホルダで未達を明記 |
