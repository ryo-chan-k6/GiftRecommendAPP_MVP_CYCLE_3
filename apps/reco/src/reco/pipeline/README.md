# Phase4a pipeline scaffold

Phase4a `reco-foundation` の pipeline 骨格。各サブディレクトリは推薦パイプラインの1 phase に対応する。

| Phase | ディレクトリ | 責務（将来） |
| ----- | ------------ | ------------ |
| input_parse | `input_parse/` | `RecommendationRequest` の検証・正規化 |
| user_feature | `user_feature/` | User Feature 生成 |
| retrieval | `retrieval/` | 候補商品取得 |
| matching | `matching/` | context_score / feature match 算出 |
| ranking | `ranking/` | final_score / rank 決定 |
| reason | `reason/` | 推薦理由生成 |

`PipelineContext.recommendation_request` は `reco.domain.recommendation.RecommendationRequest` を保持する。
Phase4a では `input_parse` が request_id から placeholder を生成する scaffold のみ。

正本ディレクトリ構成: `docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md` §7.3

Orchestration 入口: `PipelineRunner`（`runner.py`）
