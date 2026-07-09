# packages/test-fixtures

Gift Recommendation Service MVP の packages / apps 横断で再利用するテスト fixture パッケージ。

## 目的

- web / api / reco / batch / packages から共通参照できる fixture 正本を提供する
- manifest 索引と loader で fixture パス解決を統一する
- 単体テスト向けの最小サンプルデータを Phase4a scope 内で整備する

## 責務分担

| 配置 | 役割 |
| ---- | ---- |
| `packages/test-fixtures/` | packages / apps 横断の再利用 fixture（本パッケージ） |
| `tests/fixtures/` | Layer2 システム/品質テスト用 fixture（Epic C C2 正本） |
| `supabase/seeds/test-data/` | DB test seed（master seed とは分離） |

## ディレクトリ構成

| パス | 役割 |
| ---- | ---- |
| `fixtures/manifest.json` | fixture 索引 |
| `fixtures/feature/` | Feature ベクトル等の単体テスト用 fixture |
| `fixtures/recommendation/` | Recommendation Request 等の単体テスト用 fixture |
| `src/` | TypeScript loader（`@gift-recommendation/test-fixtures`） |
| `src/gift_recommendation/test_fixtures/` | Python loader（reco / batch 向け） |

## 利用例（TypeScript）

```typescript
import {
  loadMvpUserFeaturesBaseline,
  loadRecommendationRequestBossThanksMinimal,
} from "@gift-recommendation/test-fixtures";

const features = await loadMvpUserFeaturesBaseline();
const request = await loadRecommendationRequestBossThanksMinimal();
```

## 利用例（Python）

```python
from gift_recommendation.test_fixtures import (
    load_mvp_user_features_baseline,
    load_recommendation_request_boss_thanks_minimal,
)

features = load_mvp_user_features_baseline()
request = load_recommendation_request_boss_thanks_minimal()
```

## 開発

```bash
cd packages/test-fixtures
pnpm install
pnpm test

# Python（ルート workspace 推奨）
../../scripts/dev/setup-python.sh
../../scripts/dev/pytest-python.sh
```

正本: [DevOps方針書](../../docs/05_アプリケーション設計/共通/DevOps方針書.md) §8.2 / [プロジェクトディレクトリ構成定義書](../../docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md) §8
