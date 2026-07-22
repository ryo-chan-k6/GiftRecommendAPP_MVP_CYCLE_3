# Reco性能フィジビリティ検証結果 Phase3 Reason 込み E2E

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | PoC 検証結果（Phase3 Reason 込み E2E） |
| 検証ID | TV-007 |
| 検証モード | `live`（ephemeral DB + OpenAI mock / secrets） |
| 関連 Epic | [#1535](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1535) |
| 関連 Task | [#1536](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1536) |
| 判定基準の正 | [#1533](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1533) / MOD-RECO-001 §13.2（Epic #1532 Branch 上の確定文） |
| 計画書 | [Reco性能フィジビリティ検証計画書](./Reco性能フィジビリティ検証計画書.md) |
| Phase2 結果 | [Reco性能フィジビリティ検証結果_Phase2_live](./Reco性能フィジビリティ検証結果_Phase2_live.md) |
| 計測日 | 2026-07-22（JST） |

**注意:** 本結果の Go / Adjust / Block は **実測根拠付きの暫定判定**である。`phase_output` soft/hard は #1553 で案 A（3s/7s）を**暫定据置**確定（最終引き下げは後続）。Reason 込み E2E は同期外部 AI 込み 6s/8s 同一枠を維持。

---

## 2. 実施概要

| 項目 | 内容 |
| ---- | ---- |
| ハーネス | `scripts/perf/reco_pipeline_bench.py --mode live`（Phase3: Reason 込みを primary_scope） |
| 実行経路 | `RecommendationOrchestrator` + `CompositionMode.PRODUCTION`（HTTP 非経由） |
| OpenAI | `scripts/perf/openai_bench_clients.py` 差込（`apps/reco/src/**` 変更なし） |
| DB | GHA ephemeral Supabase + local Docker Supabase（同一 seed 手順） |
| 代表入力 | `friend_casual` × `birthday`、`top_k=5`、`candidate_limit=100`、`--force-llm`（secrets） |
| hard timeout | 計測のため bypass（`--enforce-hard-timeout` 未使用） |
| apps/reco 変更 | なし |

### 2.1 主対象と分離判定（Phase3）

| スコープ | 区間 | 判定枠（#1533） |
| -------- | ---- | --------------- |
| **主対象** | 入力解析〜 Reason（最終レスポンス） | 同期外部 AI 込み soft **6,000ms** / hard **8,000ms** |
| 比較 | 入力解析〜 Ranking | Reco 内部 soft **1,500ms** / hard **2,000ms**（mock 主。secrets は User Meaning 支配のため参考） |
| 必須指標 | `phase_output`（reason step） | #1553 暫定据置 soft **3,000ms** / hard **7,000ms**（新定義は §3.3.2 / §3.3.3） |

### 2.2 GHA 実行記録

| Run ID | モード | iterations | 結果 | URL |
| ------ | ------ | ---------- | ---- | --- |
| 29854691042 | live + secrets（`--force-llm`） | 20 | success | [Actions](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/29854691042) |
| 29855026956 | live + mock | 20 | success | [Actions](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/29855026956) |

artifact: `reco-perf-bench-<run_id>`（`report.json`, `summary.md`）。secret 実値は成果物・ログに含まれていない。

### 2.3 local 実行

| 項目 | 状態 |
| ---- | ---- |
| Docker / Supabase | 起動確認済み |
| migrate / seed | item=3 |
| local live + mock | **実施**（iterations=20, warmup=2）→ Reason E2E p95≈2,089ms **Go** / Ranking まで p95≈709ms **Go** |
| local live + secrets | **実施**（2026-07-22 再計測、iterations=20, warmup=2, `--force-llm`）→ Reason E2E p95≈6,504ms **Adjust** / Ranking まで p95≈2,949ms **Block**（参考）/ phase_output p95≈3,555ms。embedding_calls=22 / llm_calls=22 |

---

## 3. live 実測結果

### 3.1 Reason 込み E2E（主対象: input_parse → reason）

| 環境 | openai_mode | iterations | p50 (ms) | p95 (ms) | max (ms) | 暫定判定（vs 6s/8s） |
| ---- | ----------- | ---------- | -------- | -------- | -------- | --------------------- |
| GHA | secrets | 20 | 4,963.5 | **12,483.9** | 16,547.0 | **Block**（p95 > hard 8,000） |
| local（WSL2） | secrets | 20 | 5,192.5 | **6,504.4** | 8,051.0 | **Adjust**（soft < p95 ≤ hard） |
| local（WSL2） | mock | 20 | 1,729.0 | **2,089.2** | 2,131.0 | **Go**（p95 ≤ soft 6,000） |
| GHA | mock | 20 | 1,148.0 | **1,247.3** | 1,252.0 | **Go**（p95 ≤ soft 6,000） |

**事実:** secrets 経路（GHA / local）はいずれも embedding_calls=22 / llm_calls=22（warmup 含む）。mock は calls=0。いずれも success_count=20/20。

### 3.1.1 GHA ↔ local 再現性（secrets / Reason 込み）

| 指標 | GHA | local | 判定 |
| ---- | --- | ----- | ---- |
| Reason E2E p95 (ms) | 12,483.9 | 6,504.4 | GHA **Block** / local **Adjust**（hard 境界の環境差。Phase2 と同型） |
| phase_output p95 (ms) | 6,424.0 | 3,555.1 | 両環境とも当面 500ms 超過 |
| user_meaning p95 (ms) | 5,872.9 | 2,640.1 | GHA は phase hard 5,000ms 超過 / local は以内 |

**解釈（推論）:** secrets は OpenAI レイテンシ変動で 6s/8s 前後に振れる。local は Adjust、GHA は Block。いずれも User Meaning + Reason が支配要因。

### 3.2 Ranking まで（比較: input_parse → ranking）

| 環境 | openai_mode | p50 (ms) | p95 (ms) | 暫定判定（vs Reco 内部 1.5s/2s） |
| ---- | ----------- | -------- | -------- | -------------------------------- |
| GHA | secrets | 2,285.0 | **6,059.9** | **Block**（User Meaning 支配。内部枠への当てはめは参考） |
| local（WSL2） | secrets | 2,351.0 | **2,949.4** | **Block**（同上・参考） |
| local（WSL2） | mock | 565.5 | **709.4** | **Go** |
| GHA | mock | 389.0 | **431.4** | **Go** |

### 3.3 phase_output（reason step）

| 環境 | openai_mode | p50 (ms) | p95 (ms) | max (ms) | 当面記載 hard 500ms |
| ---- | ----------- | -------- | -------- | -------- | ------------------- |
| GHA | secrets | 2,678.5 | **6,424.0** | 8,457.0 | 大幅超過 |
| local（WSL2） | secrets | 2,843.0 | **3,555.1** | 4,335.0 | 大幅超過 |
| local（WSL2） | mock | 1,151.5 | **1,355.0** | 1,431.0 | 超過 |
| GHA | mock | 759.0 | **816.4** | 824.0 | 超過 |

#### 3.3.1 計測上の注意（`phase_output` の読み方）

##### 旧定義（Phase3 初版〜#1545 前）— §3.3 表の根拠

**事実:** 当時の bench の `reason` / `phase_output` は Orchestrator phase_log の次を合算していた。

| phase_name | 内容 |
| ---------- | ---- |
| `result_generated` | MOD-RECO-021（短い） |
| `reason_generated` | MOD-RECO-023 Reason Generator |
| `response_built` | **パイプライン開始からの累積壁時計**（`recommendation_latency_ms`） |

そのため §3.3 表の数秒級 `phase_output` は **Reason 単体の OpenAI レイテンシではない**。追加デバッグ（local secrets・1 run）では `reason_generated` ≈ **50ms**、`response_built` が累積数秒を占めた。

**事実:** 本計測条件では `RECO_REASON_LLM_REFINEMENT_ENABLED` 未設定（既定 `false`）のため、Reason の LLM refinement は **OFF**。`--force-llm` が誘発するのは主に **User Meaning（Semantic LLM）** である。

##### 新定義（#1545 以降）

**事実:** `LIVE_PHASE_TO_STEP` / `phase_output` 合算から `response_built` を除外した。

| 定義 | 含む phase | report 上の扱い |
| ---- | ---------- | --------------- |
| **新** `phase_output` / `reason` | `result_generated` + `reason_generated` | `scopes.phase_output` |
| `response_built`（診断） | `response_built` のみ | `scopes.response_built`（合算対象外） |
| Reason 込み E2E | 外側 wall-clock | 変更なし（soft 6s / hard 8s） |

**推論:** §5 の案 A（soft 3s / hard 7s）は **旧合算値**を根拠としている。新定義では `phase_output` が大幅に小さくなるため、案 A の見直し要否は Human 判断（断定しない）。

**本 Task の扱い:** 性能改善（User Meaning の短縮・キャッシュ・非同期・モデル選定、ボリューム/複雑条件、OKURI UX 横断）は **別 Task**。本結果の §3 表は旧定義の記録として残し、新定義の再計測は §3.3.2 に記録する。

#### 3.3.2 #1545 再計測（新定義・local mock）

| 項目 | 値 |
| ---- | -- |
| 日時 | 2026-07-22 |
| 環境 | local（WSL2） |
| openai_mode | mock |
| iterations / warmup | 20 / 2 |
| success | 20 / 20 |
| 定義 | `phase_output` = `result_generated` + `reason_generated`（`response_built` 除外） |
| 出力 | `scripts/perf/output-metric-fix-mock/`（Git 管理外） |

| 指標 | 旧定義（§3.3 local mock） | 新定義（本節） | 差分の読み方 |
| ---- | ------------------------- | -------------- | ------------ |
| phase_output p50 (ms) | 1,151.5 | **86.5** | 旧は累積合算込み |
| phase_output p95 (ms) | **1,355.0** | **105.1** | 新は Reason/Output 寄与寄り（約 **1/13**） |
| response_built p95 (ms) | （旧は合算内） | **1,233.2** | 診断専用。累積壁時計 |
| Reason E2E p95 (ms) | 2,089.2 | **1,234.0** | E2E 定義は変更なし（wall-clock）。実行差あり |
| Ranking まで p95 (ms) | 709.4 | **685.1** | 比較枠。定義変更の対象外 |

**事実:** 新定義では `phase_output` p95 が旧合算（1,355ms）から **105ms** へ低下し、`response_built`（≈E2E 累積）と分離できた。

**転帰（#1553）:** Human は案 A（soft 3s / hard 7s）を**暫定据置**。secrets 再計測は必須として §3.3.3 で実施。最終引き下げは後続 Human。

#### 3.3.3 #1553 再計測（新定義・local secrets）

| 項目 | 値 |
| ---- | -- |
| 日時 | 2026-07-22 |
| 環境 | local（WSL2） |
| openai_mode | secrets |
| iterations / warmup | 20 / 2 |
| success | 20 / 20 |
| 定義 | `phase_output` = `result_generated` + `reason_generated`（`response_built` 除外） |
| 出力 | `scripts/perf/output-metric-fix-secrets/`（Git 管理外） |

| 指標 | 新定義 local mock（§3.3.2） | 新定義 local secrets（本節） |
| ---- | --------------------------- | ---------------------------- |
| phase_output p50 (ms) | 86.5 | **86.0** |
| phase_output p95 (ms) | **105.1** | **109.1** |
| response_built p95 (ms) | 1,233.2 | **3,467.5** |
| Reason E2E p95 (ms) | 1,234.0 | **3,468.2**（Go vs 6s/8s） |
| Ranking まで p95 (ms) | 685.1 | **3,083.0**（Block vs 内部 1.5s/2s・User Meaning 支配） |
| user_meaning p95 (ms) | （mock） | **2,835.0** |

**事実:** secrets でも新定義 `phase_output` p95 は **109ms** 帯で mock と同規模。E2E / Ranking までの遅延は User Meaning（および累積 `response_built`）側。

**推論:** 暫定据置の 3s/7s は新定義監視枠としては余裕が大きい。最終引き下げ候補は後続 Human（断定しない）。secret 実値は成果物に含めない。

### 3.4 フェーズ別 p95（secrets）

| TV-007 step | measurement_point | GHA p95 (ms) | local p95 (ms) | §13.2 hard（#1533） | 所見 |
| ----------- | ----------------- | ------------ | -------------- | ------------------- | ---- |
| input_parse | phase_config | 128.5 | 195.3 | 300 | 上限内 |
| user_feature | phase_user_meaning | **5,872.9** | 2,640.1 | 5,000 | GHA のみ超過 |
| retrieval | phase_retrieval | 77.7 | 125.6 | 1,000 | 上限内 |
| matching | phase_matching | 10.2 | 16.2 | 500 | 上限内 |
| ranking | phase_ranking | 10.1 | 17.2 | 1,000 | 上限内 |
| reason | phase_output | **6,424.0** | **3,555.1** | 当面 500（旧）→ **#1553 暫定 3s/7s** | **旧合算値**（§3.3.1）。新定義は §3.3.2 / §3.3.3（p95≈105–109ms） |

### 3.5 mock vs secrets（Reason 込み）

| 環境 | openai_mode | Reason E2E p95 (ms) | phase_output p95 (ms) | user_meaning p95 (ms) |
| ---- | ----------- | ------------------- | --------------------- | --------------------- |
| GHA | mock | 1,247.3 | 816.4 | 224.1 |
| local | mock | 2,089.2 | 1,355.0 | 379.3 |
| GHA | secrets | 12,483.9 | 6,424.0 | 5,872.9 |
| local | secrets | 6,504.4 | 3,555.1 | 2,640.1 |

**解釈（事実）:** secrets の Reason 込み E2E 遅延の主因は **User Meaning（Semantic LLM + Embedding）**。Retrieval / Matching / Ranking は余裕。§3.3 表の `phase_output` は旧定義（`response_built` 累積合算）であり、Reason LLM 支配とは読めない（本条件では Reason LLM OFF）。新定義の mock 再計測は §3.3.2。

---

## 4. #1533 soft/hard に対する分離判定

### 4.1 判定ルール

| スコープ | soft | hard | ラベル |
| -------- | ---- | ---- | ------ |
| Ranking まで vs Reco 内部 | 1,500ms | 2,000ms | p95≤soft→Go / soft<p95≤hard→Adjust / p95>hard→Block |
| Reason 込み vs 同期外部 AI 込み | 6,000ms | 8,000ms | 同上 |

### 4.2 暫定判定表

| 計測系 | Ranking まで（内部枠） | Reason 込み（外部 AI 込み枠） | 根拠 |
| ------ | ---------------------- | ----------------------------- | ---- |
| live + secrets（GHA） | **Block**（参考） | **Block** | Reason E2E p95=12,484ms > 8,000。Ranking までも User Meaning で内部枠超過 |
| live + secrets（local） | **Block**（参考） | **Adjust** | Reason E2E p95=6,504ms（soft 超過・hard 以内）。Ranking まで p95=2,949ms |
| live + mock（GHA） | **Go** | **Go** | Ranking 431ms / Reason E2E 1,247ms |
| live + mock（local） | **Go** | **Go** | Ranking 709ms / Reason E2E 2,089ms |

**PoC としての整理（推論）:** mock は両枠とも成立。secrets 主経路の Reason 込みは環境により **Block〜Adjust**（GHA / local）。ボトルネックは **User Meaning の同期外部 AI**（Semantic LLM + Embedding）。Reco 内部（Retrieval〜Ranking）は Phase2 同様 Go 寄り。性能改善の具体策はデータパターン検証・UX 考慮のうえ **別 Task**。

---

## 5. phase_output 上限（#1553 Human 暫定据置）

| 案 | soft（監視） | hard（中断/上限） | 根拠・意図 |
| -- | ------------- | ----------------- | ---------- |
| **A（#1553 暫定据置）** | **3,000ms** | **7,000ms** | 旧合算根拠の案 A を暫定維持。新定義整合・secrets 再計測済み |
| B（候補） | 2,500ms | 5,000ms | より厳しい。最終引き下げ候補 |
| C（候補） | 監視のみ（soft 3,000） | hard なし（§10.3 fallback 継続） | Reason 失敗は fallback 可能なら hard 中断しない |
| 新定義向け（候補・推論） | 例: soft 500 / hard 2,000 | — | mock/secrets p95≈105–109ms 帯を踏まえた監視枠。**未確定** |

**#1553 確定:** 案 A を**暫定据置**。Reason 込み E2E は 6s/8s 同一枠を維持。secrets 再計測は必須として実施（§3.3.3）。

**後続 Human:** 新定義実測を踏まえた最終引き下げ（B / 新定義向け案等）。

---

## 6. 設計反映メモへの入力

| 対象 | Phase3 からの入力案 |
| ---- | ------------------- |
| Reason 込み E2E | secrets: Block（12.5s p95・旧 GHA）。新定義 local secrets: Go（p95≈3.5s）。6s/8s 同一枠維持（#1553） |
| phase_output | **#1553 暫定据置:** soft 3,000 / hard 7,000。新定義 mock/secrets p95≈105–109ms |
| Ranking まで | mock は内部 1.5s/2s で Go。Phase2 結論を維持 |
| 正式 docs | #1553 で暫定据置反映済み。最終引き下げは後続 |

---

## 7. 残リスク・未実施

| 項目 | 内容 |
| ---- | ---- |
| secrets 環境差 | GHA Block / local Adjust。最終ラベルは Human 判断 |
| phase_output 計測定義 | #1545 で `response_built` を除外（新定義）。§3 表は旧定義の記録 |
| phase_output 上限 | #1553 で案 A **暫定据置**。最終引き下げは後続 Human |
| 性能改善 | User Meaning 短縮/キャッシュ/非同期/モデル、ボリューム・複雑条件、UX 横断は別 Task |
| 件数スケール | seed 3 件。100/500/1,000 未実施（Phase2 同） |
| hard timeout 有効時 | bypass 計測。本番 8s 中断時の挙動は別確認候補 |
| concurrency | 同一 Branch で mock/secrets 同時 dispatch すると後勝ちで cancel。逐次実行が必要 |
| secret | 実値は成果物に含めない |
| secrets 再計測（新定義） | mock §3.3.2 / secrets §3.3.3（#1553 実施済） |

---

## 8. 変更履歴

| 日付 | 変更内容 |
| ---- | -------- |
| 2026-07-22 | Phase3 Reason 込み E2E 初版（GHA secrets/mock + local mock） |
| 2026-07-22 | local secrets 再計測を追記（Reason E2E Adjust）。GHA/local 再現性を更新 |
| 2026-07-22 | `phase_output` 計測定義の注意（`response_built` 累積合算・Reason LLM OFF）を追記 |
| 2026-07-22 | #1545: `phase_output` から `response_built` 除外。新旧定義と mock 再計測（§3.3.2）を追記 |
| 2026-07-22 | #1553: 案 A 暫定据置。local secrets 再計測（§3.3.3・p95≈109ms）と §5 転帰を追記 |
