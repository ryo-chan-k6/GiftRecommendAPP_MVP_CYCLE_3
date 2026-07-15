# Experiment: レーン1e UserFeature Postgres 配線

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-15 |
| Issue | #1274 |
| Epic | #1268 |
| 目的 | GRS-REC-006（user_feature row count mismatch）解消確認 |

## 実施内容

- `PostgresAwareUserFeatureRepository`（insert / get / has_user_semantic）
- `PostgresNormalizationRuleRepository`（binding + `is_current` fallback）
- MOD-RECO-008/009 への共有注入
- `PostgresRunValidation.get_embedding_model_version_id`

## 結果（事実）

| 項目 | 結果 |
| ---- | ---- |
| UT | composition + repo UT 通過 |
| PUB-002 | HTTP 500 `GRS-REC-012` |
| user_feature | DB INSERT 成功（8 行 / Run） |
| 旧 GRS-REC-006 | 解消 |

## 補足

- 初回失敗原因: InMemory の `fnv-mvp-sigmoid-default` は UUID 列に INSERT 不可 → Normalization Postgres + fallback で解消
- `normalization_rule` テーブルは現状未seed。fallback で縦串継続可能。seed 正本化は後続候補

## 次 Blocker（推論）

`ranked_items is required on execution_context` — retrieval / ranking stub。別 Task/Epic。
