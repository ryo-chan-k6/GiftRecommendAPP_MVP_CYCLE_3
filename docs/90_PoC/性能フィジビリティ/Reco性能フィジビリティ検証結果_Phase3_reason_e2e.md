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

**注意:** 本結果の Go / Adjust / Block は **実測根拠付きの暫定判定**である。`phase_output` hard 最終値と、Reason 込み E2E を同期外部 AI 込み 6s/8s と同一枠にするかは Human Review で確定する。正式 docs への `phase_output` 反映は out of scope（別 Task 可）。

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
| 必須指標 | `phase_output`（reason step） | 上限は本結果で案出し（Human 未確定） |

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

### 3.4 フェーズ別 p95（secrets）

| TV-007 step | measurement_point | GHA p95 (ms) | local p95 (ms) | §13.2 hard（#1533） | 所見 |
| ----------- | ----------------- | ------------ | -------------- | ------------------- | ---- |
| input_parse | phase_config | 128.5 | 195.3 | 300 | 上限内 |
| user_feature | phase_user_meaning | **5,872.9** | 2,640.1 | 5,000 | GHA のみ超過 |
| retrieval | phase_retrieval | 77.7 | 125.6 | 1,000 | 上限内 |
| matching | phase_matching | 10.2 | 16.2 | 500 | 上限内 |
| ranking | phase_ranking | 10.1 | 17.2 | 1,000 | 上限内 |
| reason | phase_output | **6,424.0** | **3,555.1** | 未確定（当面 500） | 両環境で主ボトルネックの一つ |

### 3.5 mock vs secrets（Reason 込み）

| 環境 | openai_mode | Reason E2E p95 (ms) | phase_output p95 (ms) | user_meaning p95 (ms) |
| ---- | ----------- | ------------------- | --------------------- | --------------------- |
| GHA | mock | 1,247.3 | 816.4 | 224.1 |
| local | mock | 2,089.2 | 1,355.0 | 379.3 |
| GHA | secrets | 12,483.9 | 6,424.0 | 5,872.9 |
| local | secrets | 6,504.4 | 3,555.1 | 2,640.1 |

**解釈（事実）:** secrets では User Meaning と Reason（いずれも同期 LLM）が支配要因。Retrieval / Matching / Ranking は余裕。

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

**PoC としての整理（推論）:** mock は両枠とも成立。secrets 主経路の Reason 込みは環境により **Block〜Adjust**（GHA / local）。ボトルネックは User Meaning + Reason の同期外部 AI。Reco 内部（Retrieval〜Ranking）は Phase2 同様 Go 寄り。

---

## 5. phase_output 上限案（Human 未確定）

| 案 | soft（監視） | hard（中断/上限） | 根拠・意図 |
| -- | ------------- | ----------------- | ---------- |
| A（推奨・推論） | **3,000ms** | **7,000ms** | secrets p50≈2.7–2.8s / p95≈3.6–6.4s（local/GHA）。E2E hard 8s 内に Reason 予算を確保 |
| B | 2,500ms | 5,000ms | より厳しい。現行 secrets p95 では未達 → 実装最適化前提 |
| C | 監視のみ（soft 3,000） | hard なし（§10.3 fallback 継続） | Reason 失敗は fallback 可能なら hard 中断しない |

**推論:** 当面記載の 500ms は mock でも超過しており非現実的。正式反映 Task では案 A を起点に Human が採否する。

**Human 判断依頼:**

1. `phase_output` hard 最終値（案 A/B/C または別値）
2. Reason 込み E2E を同期外部 AI 込み **6s/8s と同一枠**にするか（本結果は同一枠で判定済み。枠を分ける場合は別 soft/hard が必要）

---

## 6. 設計反映メモへの入力

| 対象 | Phase3 からの入力案 |
| ---- | ------------------- |
| Reason 込み E2E | secrets: Block（12.5s p95）。mock: Go。6s/8s 同一枠で判定した場合の根拠 |
| phase_output | 案 A: soft 3,000 / hard 7,000（未確定） |
| Ranking まで | mock は内部 1.5s/2s で Go。Phase2 結論を維持 |
| 正式 docs | `phase_output` のみ別 Task（#1533 宣言どおり） |

---

## 7. 残リスク・未実施

| 項目 | 内容 |
| ---- | ---- |
| secrets 環境差 | GHA Block / local Adjust。最終ラベルは Human 判断 |
| 件数スケール | seed 3 件。100/500/1,000 未実施（Phase2 同） |
| hard timeout 有効時 | bypass 計測。本番 8s 中断時の挙動は別確認候補 |
| concurrency | 同一 Branch で mock/secrets 同時 dispatch すると後勝ちで cancel。逐次実行が必要 |
| secret | 実値は成果物に含めない |

---

## 8. 変更履歴

| 日付 | 変更内容 |
| ---- | -------- |
| 2026-07-22 | Phase3 Reason 込み E2E 初版（GHA secrets/mock + local mock） |
| 2026-07-22 | local secrets 再計測を追記（Reason E2E Adjust）。GHA/local 再現性を更新 |
