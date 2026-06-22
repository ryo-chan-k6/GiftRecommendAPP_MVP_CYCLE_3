# Phase4a domain scaffold

Phase4a `reco-foundation` の domain 中核骨格。推薦ドメインの集約・値オブジェクトの配置先。

| サブディレクトリ | 責務（将来） | ドメインモデル参照 |
| ---------------- | ------------ | ------------------ |
| `recommendation/` | Recommendation Request / Run / Result | ドメインモデル §4.1〜4.2 |
| `recommendation/inputs.py` | Request 入力値オブジェクト（relationship / preferred 等） | RecommendationRequest定義書 §6 |
| `gift_meaning/` | MVP 8次元 Feature、Gift Meaning Space | ドメインモデル §2.3〜2.4 |
| `user_meaning/` | User Meaning 生成結果 | ドメインモデル §4.3 |
| `item_meaning/` | Item Meaning 表現 | ドメインモデル §4.4 |
| `matching/` | context_score / 意味一致度 | Matching定義書 |

正本ディレクトリ構成: `docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md` §7.3

`RecommendationRequest` は OpenAPI `NormalizedRecommendationRequest` に対応する型骨格を Phase4a で先に定義する。validation・DB mapping は Phase4b 以降。

Phase4b 以降、`packages/shared-logic` の Feature 演算と統合する。
