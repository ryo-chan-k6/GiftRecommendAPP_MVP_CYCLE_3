# Human Decision Log

## 1. 概要

| 項目          | 内容 |
| ------------- | ---- |
| Log ID        | `2026-06-10-semantic-config-version-public-reference-join-policy` |
| Log種別       | `human-decision` |
| 件名          | semantic_config_version Public 参照キーと config_name 解決方針 |
| 発生日時      | 2026-06-10 |
| 記録日時      | 2026-06-10 |
| 発生元        | Task #463 設計レビュー（human-led） |
| 関連Issue     | `#463` |
| 親 Epic       | `#435` |
| 関連PR        | （未作成） |
| 重要度        | `high` |
| 状態          | `resolved` |

---

## 2. 結論

`semantic_config_version` に関する Public 参照と `config_name` 解決を以下とする。

### 2.1 Public 参照キー

| 項目 | 決定 |
| ---- | ---- |
| Public 参照 | **`configName` + `versionLabel` の composite** |
| 不採用 | 単一 `semanticConfigVersionId` 表面 ID（例: `semantic_config_v001`） |
| 内部参照 | `semantic_config_version_id`（UUID）は非公開のまま Run / 子テーブル / 派生データに使用 |

### 2.2 `version_label`

| 項目 | 決定 |
| ---- | ---- |
| 形式 | semver 基本形（MVP 初期値: `v1.0.0`） |
| DB CHECK | `^v[0-9]+\.[0-9]+\.[0-9]+$`（`semantic_config_version_テーブル定義書` §10） |

### 2.3 `config_name` 解決

| 項目 | 決定 |
| ---- | ---- |
| 正本 | 親テーブル `semantic_config.config_name` のみ |
| denormalize | **しない**（`semantic_config_version` に `config_name` 列を追加しない） |
| DB ビュー | **作成しない**（MVP） |
| api 解決 | IF-DB-API-005 で `semantic_config` と `semantic_config_version` を **アプリ層 JOIN** |
| reco 解決 | IF-DB-RECO-001 は `semantic_config_version` 表中心。親 JOIN は api マスタ参照に限定 |

### 2.4 後続作業

| 対象 | 方針 |
| ---- | ---- |
| API-PUB-007 / API-PUB-008 / API-INT-002 | Contract Task で契約・OpenAPI を composite 参照に追随 |
| `semantic_config_テーブル定義書`（Task #462） | 親正本・api JOIN 参照の補足を追随検討 |

---

## 3. 判断理由（要約）

- 単一 `version_label` 列では `semanticConfigVersionId` と `versionLabel` の二重表現が矛盾していた（旧 §17 No.2）
- `config_name` の denormalize は正本重複と整合コストが増える
- DB ビューは先例がなく、MVP では api Repository の JOIN で十分
- `ranking_config` と同様、Public には人間可読な composite、内部には UUID を維持する構成が一貫する

---

## 4. 正本への反映

| 正本 | 反映内容 |
| ---- | -------- |
| `docs/06_実装設計/database/semantic_config_version_テーブル定義書.md` | §5.3 / §5.3.1 / §17.1 |
| `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §8 補足 |
| `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-DB-API-005 補足 |

---

### 2.5 解決階層（`is_active` → `is_current`）

| 層 | 決定 |
| ---- | ---- |
| 第 1 層 | 親 `semantic_config.is_active = true` の系列のみ対象 |
| 第 2 層 | 対象系列内で `is_current = true` の version を解決 |
| 系列無効時 | `is_active = false` の系列に属する version は解決対象外（GRS-CFG-002） |

### 2.6 `is_current` の解決単位

| 項目 | 決定 |
| ---- | ---- |
| 解決単位 | **`semantic_config_id` 単位**（設定系列ごと） |
| 制約 | 同一 `semantic_config_id` で `is_current = true` は最大 1 行 |
| 不採用 | システム全体で `is_current = true` を 1 件に制限する方式 |

---

### 2.7 `valid_from` / `valid_to`（MVP seed）

| 項目 | 決定 |
| ---- | ---- |
| seed 設定 | **明示設定する**（MVP 初期 seed で NULL は使わない） |
| `valid_from` | seed 投入日時（`created_at` と同値可） |
| `valid_to` | **`9999-12-31 23:59:59+00`（UTC）**（未来日付の上限・実質無期限） |
| 現行解決 | `is_active` → `is_current` を主とし、期間による解決は MVP 必須にしない |

### 2.8 `recommendation_run` / `evaluation_run` への FK

| 項目 | 決定 |
| ---- | ---- |
| MVP | **LOGICAL 参照を維持**（物理 FK なし） |
| 理由 | `model_version` / `ranking_config` と同型。再現性は version 行の物理 DELETE 禁止 + Run 側 ID 固定で担保 |
| 整合担保 | reco Run INSERT 前の存在確認 + run 表の `semantic_config_version_id` Index |
| 将来 | `recommendation_run` 定義 Task で物理 FK ON + DELETE RESTRICT をオプション検討 |

---

## 5. 未決事項（本判断の対象外）

（Task #463 時点で主要論点は §17.1 に移管済み）
