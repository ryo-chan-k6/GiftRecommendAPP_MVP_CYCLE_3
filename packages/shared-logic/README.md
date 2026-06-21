# packages/shared-logic

Gift Recommendation Service MVP の reco / batch 共通ドメインロジック（Python）。

## 目的

- Feature Engine・正規化・Meaning 射影の共通中核を提供する
- User Feature / Item Feature で同一ルールを適用し、Gift Meaning Space 上で比較可能にする
- `packages/code-definitions/` の `feature_code` を正本として MVP 8 軸を扱う

## 責務分担

| パッケージ | 役割 |
| ---------- | ---- |
| `code-definitions` | Feature / Semantic / error_code 等の YAML 正本 |
| `shared-types` | TypeScript 向けカタログ型・runtime ガード |
| `shared-logic` | reco / batch 共通の Feature Engine・正規化・Meaning 射影 |

## モジュール構成

| モジュール | 役割 |
| ---------- | ---- |
| `constants` | MVP 8 軸 Feature コード、Social / Symbolic 区分 |
| `catalog` | `code-definitions` から `feature_code` をロード |
| `feature_engine` | Feature delta 統合・値域クリップ |
| `normalization` | raw Feature の正規化（MVP: rule-based clip） |
| `meaning_projection` | 正規化 Feature から Social / Symbolic 座標へ射影 |

## 利用例

```python
from gift_recommendation.shared_logic import (
    integrate_feature_deltas,
    load_mvp_feature_codes,
    normalize_features,
    project_to_meaning,
)

feature_codes = load_mvp_feature_codes()
raw = integrate_feature_deltas(
    {},
    {"formality": 0.8, "safety": 0.9, "brand_appropriateness": 0.7},
    feature_codes=feature_codes,
)
normalized = normalize_features(raw, feature_codes=feature_codes)
meaning = project_to_meaning(normalized, feature_codes=feature_codes)
```

## 開発

```bash
cd packages/shared-logic
python -m pip install -e ".[dev]"
pytest
```

## 変更手順

1. 関連 docs（GiftMeaningSpace定義書、Featureルール定義書等）更新
2. `packages/code-definitions/` 更新（必要時）
3. 本パッケージの catalog / 射影 / 正規化整合確認（`pytest`）
4. reco / batch 利用側更新（後続 Task）

正本: [GiftMeaningSpace定義書](../../docs/04_ドメインモデル設計/GiftMeaningSpace定義書.md) §5–§7 / [DevOps方針書](../../docs/05_アプリケーション設計/共通/DevOps方針書.md) §5.5
