# Experiment: レーン1e UserSemantic Postgres 配線

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-15 |
| Issue | #1272 |
| Epic | #1268 |
| 目的 | GRS-REC-005（user_semantic not found）解消確認 |

## 実施内容

- `PostgresUserSemanticRepository`（exists / insert）
- `PostgresAwareUserFeatureRepository.has_user_semantic` → `user_semantic` テーブル
- `build_production_ports` へ注入（DEFAULT InMemory 維持）

## 結果（事実）

| 項目 | 結果 |
| ---- | ---- |
| UT | composition + 新規 repo UT 通過 |
| PUB-002 | HTTP 500 `GRS-REC-006` |
| user_semantic | DB INSERT 成功（concepts > 0） |
| 旧 GRS-REC-005 | 解消 |

## 次 Blocker（推論）

`user_feature row count mismatch ...: 0` — 後続が Postgres の `user_feature` を読む一方、INSERT は memory のまま。別 Task で Postgres 永続が必要。
