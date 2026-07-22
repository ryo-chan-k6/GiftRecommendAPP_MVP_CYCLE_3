# 外部AI API疎通検証結果（TV-005）

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | PoC 検証結果 |
| 検証ID | TV-005 |
| 計画 | [外部AI_API疎通検証計画](./外部AI_API疎通検証計画.md) |
| 方針 | [TV-005_外部AI_API疎通](../計画/TV要件・実施方針/TV-005_外部AI_API疎通.md) |
| 関連 Epic / Task | [#1565](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1565) / [#1566](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1566) |
| 計測日 | 2026-07-22（JST） / secrets `measured_at_utc=2026-07-22T12:08:47Z` |
| 設計反映メモ | [設計反映メモ](./設計反映メモ.md) |

**注意:** 本結果の Go / Adjust / Block は **TV-005（API 単体疎通・制約・コスト）** の暫定判定である。Reco E2E の性能判定は TV-007 を正とする。

---

## 2. 実施概要

| 項目 | 内容 |
| ---- | ---- |
| ハーネス | `scripts/perf/openai_connectivity_bench.py` |
| 環境 | local（WSL2） |
| モデル | Embedding `text-embedding-3-small` / Chat `gpt-4o-mini` |
| mock | iterations=20、`--probe-failures` |
| secrets | iterations=10、warmup=1、`--probe-failures`（invalid model 1 回） |
| apps/reco 変更 | なし（実行時に `uv` 環境の httpx のみ利用） |
| secret | `OPENAI_API_KEY` を `.env` → env 注入。成果物に実値なし |

### 2.1 TV-007 との切り分け（事実）

| 観点 | TV-005（本結果） | TV-007 |
| ---- | ---------------- | ------ |
| 計測単位 | Embedding / Chat API 単体 | Reco Orchestrator E2E 内 |
| DB / Retrieval | 不要 | ephemeral DB + seed 前提 |
| 主目的 | 疎通・失敗形式・トークン/コスト | パイプライン性能・SLO |

---

## 3. 応答時間

### 3.1 mock（HTTP 非実行）

| API | success | p50 (ms) | p95 (ms) | max (ms) |
| --- | ------- | -------- | -------- | -------- |
| embeddings | 20/20 | 2.166 | **2.261** | 2.261 |
| chat.completions | 20/20 | 5.216 | **5.257** | 5.294 |

**解釈（事実）:** mock はハーネス完走確認用。実 latency の代替にはならない。

### 3.2 secrets（実疎通）

| API | success | min (ms) | avg (ms) | p50 (ms) | p95 (ms) | max (ms) |
| --- | ------- | -------- | -------- | -------- | -------- | -------- |
| embeddings | 10/10 | 268.0 | 370.0 | 316.3 | **654.4** | 673.0 |
| chat.completions | 10/10 | 853.4 | 1401.1 | 1169.6 | **2796.3** | 4015.3 |

**解釈（事実）:** 両 API とも全件成功。Chat の方が遅く、p95 ≈ 2.8s・max ≈ 4.0s。

**解釈（推論）:** TV-007 で User Meaning が同期外部 AI 支配だった観測と整合する。本 TV の Chat 単体 p95 だけでも `phase_user_meaning` hard 5,000ms 枠内だが、Embedding + Chat + 周辺処理を合算すると余裕は限られる。

---

## 4. 失敗形式

### 4.1 mock（ローカル再現）

| api | http_status | error_kind | 記録方針 |
| --- | ----------- | ---------- | -------- |
| embeddings | 401 | auth | body は redacted。status / kind のみ |
| chat.completions | 429 | rate_limit | 同上。Retry-After の有無は実装側で扱う想定 |
| embeddings | （なし） | timeout | クライアント timeout。body なし |

### 4.2 secrets（軽量プローブ）

| api | http_status | error_kind | 備考 |
| --- | ----------- | ---------- | ---- |
| embeddings | **404** | invalid_model | 存在しないモデル名で 1 回のみ。body 非記録 |

**未実施:** rate limit の意図的大量誘発（Human 承認が必要。本 Phase では見送り）。

---

## 5. トークン / コスト概算

公開リスト単価のスナップショット（概算用。変更され得る）:

| 項目 | 単価（USD / 1M tokens） |
| ---- | ----------------------- |
| text-embedding-3-small | 0.02 |
| gpt-4o-mini input | 0.15 |
| gpt-4o-mini output | 0.60 |

### 5.1 secrets 実測トークン（10 + 10 回）

| 区分 | tokens | 概算 USD |
| ---- | ------ | -------- |
| Embedding | 110 | ≈ 0.0000022 |
| Chat prompt | 970 | — |
| Chat completion | 300 | — |
| Chat 合計 | 1,270 | ≈ 0.0003255 |
| **合計** | — | **≈ 0.0003277** |

**解釈（事実）:** PoC 規模（各 API 10 回前後）の課金は無視できる水準。

**解釈（推論）:** 本番 QPS・バッチ一括 Embedding では件数が桁違いになるため、Batch / Reco 設計では呼び出し回数とキャッシュ方針の明示が必要（正式 docs は別 Task）。

---

## 6. Go / Adjust / Block

| 観点 | ラベル | 根拠 |
| ---- | ------ | ---- |
| 疎通（Embedding / LLM） | **Go** | secrets 全件成功。mock も完走 |
| 失敗形式の観測可能性 | **Go** | mock で 401/429/timeout、secrets で 404 を status 単位で記録可能 |
| トークン/コスト感（PoC） | **Go** | 10+10 回で ≈ $0.0003。大量試験は不要と判断 |
| Reco timeout / retry 設計への示唆 | **Adjust（設計メモ）** | Chat p95≈2.8s は TV-007 / #1533 の同期外部 AI 枠（6s/8s）・`phase_user_meaning` 5s と整合する一方、合算余裕は薄い。正式反映は別 Task |
| **TV-005 総合** | **Go** | API 疎通・制約観測・コスト感の PoC 目的は達成。致命的 Block 要因なし |

---

## 7. 生データ

| モード | 出力（Git 管理外） |
| ------ | ------------------ |
| mock | `scripts/perf/output-tv005-mock/report.json` / `summary.md` |
| secrets | `scripts/perf/output-tv005-secrets/report.json` / `summary.md` |

secret 実値・Authorization・response body は含まない。

---

## 8. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-22 | 初版（#1566）。local mock / secrets 計測 |
