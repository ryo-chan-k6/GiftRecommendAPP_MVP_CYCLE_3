# Semantic Concept定義書

## 1. 概要

### 1.1 目的

本ドキュメントは、ギフトレコメンドサービスにおける `Semantic Concept` を定義する。

Semantic Conceptは、ユーザー入力・商品情報・レビュー・タグなどの自然言語情報を、Featureへ変換するための中間概念である。

本サービスでは、自然言語を直接Featureへ変換するのではなく、いったんSemantic Conceptへ変換し、その後Featureへ変換する。

```text
Natural Language
↓
Semantic Concept
↓
Feature
↓
Gift Meaning Space
```

---

### 1.2 本ドキュメントの位置づけ

| 成果物 | 本ドキュメントとの関係 |
|---|---|
| Gift Meaning Space定義書 | Semantic ConceptをFeature化した後、意味空間へ射影する |
| Feature定義書 | Semantic Conceptが影響するFeatureの定義元 |
| Featureルール定義書 | Semantic Concept → Featureの変換ルールを定義する |
| Semanticルール定義書 | 入力文・商品情報 → Semantic Conceptの変換ルールを定義する |
| Matching定義書 | Feature化されたUser / Itemを比較する |
| Ranking定義書 | Matching結果を使って最終順位を決定する |

---

### 1.3 基本方針

- Semantic Conceptは、自然言語とFeatureの間に置く中間層である
- Semantic Conceptは、意味の抽象カテゴリとして定義する
- Semantic Conceptは、User Meaning生成とItem Meaning生成の両方で利用する
- Semantic Conceptは、Feature値そのものではない
- Semantic Conceptは、原則として `semantic_config_version` に紐づけて管理する
- MVPでは初期Conceptを固定し、必要に応じて追加可能とする

---

## 2. Semantic Conceptの定義

### 2.1 Semantic Conceptとは

Semantic Conceptとは、ユーザー入力や商品情報から抽出される意味の抽象カテゴリである。

例：

| 入力表現 | Semantic Concept |
|---|---|
| 上品なもの | `formal_refined` |
| 無難なもの | `safe_classic` |
| 特別感があるもの | `special_memorable` |
| 気持ちが伝わるもの | `emotional_warm` |
| ストーリー性があるもの | `story_narrative` |

---

### 2.2 Semantic Conceptを挟む理由

自然言語からFeatureを直接算出すると、以下の問題が起きやすい。

| 問題 | 内容 |
|---|---|
| ルール複雑化 | 「上品」「高級」「きちんと」などを個別にFeatureへ変換する必要がある |
| 同義語の揺れ | 似た意味の表現を毎回別扱いしてしまう |
| 説明困難 | なぜFeature値が上がったかを説明しにくい |
| 拡張困難 | 新しい表現追加時にFeatureルールまで直接変更が必要になる |

そのため、以下の2段階に分ける。

```text
入力文・商品情報
↓
Semantic Concept
↓
Feature
```

これにより、自然言語解釈とFeature生成の責務を分離する。

---

### 2.3 Semantic ConceptとFeatureの違い

| 概念 | 役割 | 例 |
|---|---|---|
| Semantic Concept | 言語的・意味的な抽象カテゴリ | 上品、無難、特別、親しい |
| Feature | 意味を数値化する次元 | formality, safety, emotion |
| Gift Meaning Space | Featureを統合して比較する空間 | Social × Symbolic |

```text
Semantic Concept = 言葉の意味カテゴリ
Feature          = 意味を表す数値次元
```

---

## 3. Semantic Conceptの利用範囲

### 3.1 User Meaning生成での利用

User Meaning生成では、以下の入力からSemantic Conceptを抽出する。

| 入力 | 例 | 抽出されるConcept例 |
|---|---|---|
| 好み条件 | 上品なものがいい | `formal_refined` |
| 避けたい条件 | 無難すぎるものは嫌 | `not_too_safe` |
| 自由入力 | 気持ちが伝わるもの | `emotional_warm` |
| 関係性補足 | かなり親しい友人 | `close_personal` |
| 用途補足 | 記念に残るもの | `special_memorable` |

---

### 3.2 Item Meaning生成での利用

Item Meaning生成では、以下の商品情報からSemantic Conceptを抽出する。

| 入力 | 例 | 抽出されるConcept例 |
|---|---|---|
| 商品名 | 高級ギフトセット | `prestigious_quality` |
| 商品説明 | 心温まる贈り物 | `emotional_warm` |
| 商品カテゴリ | 実用雑貨 | `practical_useful` |
| 商品タグ | おしゃれ / 限定 | `stylish_aesthetic`, `special_memorable` |
| レビュー | 使いやすい / 喜ばれた | `practical_useful`, `emotional_warm` |

---

### 3.3 利用しない範囲

Semantic Conceptは、以下を直接扱わない。

| 対象 | 扱い |
|---|---|
| 価格 | budget_condition / hard_filter |
| 在庫 | 商品利用可能性 |
| 配送日 | EC連携・将来拡張 |
| 人気度 | popularity_score |
| 最終順位 | Ranking |
| リスク減点 | risk_score |
| final_score | Ranking側で算出 |

---

## 4. Semantic Conceptの構成要素

### 4.1 管理項目

Semantic Conceptは、以下の項目で定義する。

| 項目 | 内容 |
|---|---|
| concept_code | Conceptの物理名 |
| concept_label | 日本語表示名 |
| description | 意味定義 |
| polarity_default | 初期極性 |
| concept_group | Concept分類 |
| related_feature_candidates | 関連しやすいFeature候補 |
| usage_note | 利用上の注意 |

---

### 4.2 concept_code命名規則

| 項目 | ルール |
|---|---|
| 形式 | snake_case |
| 言語 | 英語 |
| 数 | 単数形または形容詞句 |
| 安定性 | 一度定義したら原則変更しない |
| 意味 | Conceptの意味が推測できる名称にする |

例：

```text
formal_refined
safe_classic
special_memorable
emotional_warm
story_narrative
```

---

### 4.3 polarity_default

`polarity_default` は、そのConceptが通常どの向きでFeatureに作用するかを表す。

| polarity | 意味 |
|---|---|
| positive | 対応Featureを強める方向 |
| negative | 対応Featureを抑制・回避する方向 |
| neutral | 文脈により判断 |
| mixed | 文脈により正負が変わる |

---

### 4.4 polarityの注意点

`negative` は「悪い意味」ではない。

本サービスにおける `negative` は、Featureの抑制・回避・過剰さの調整を表す。

例：

| Concept | polarity | 意味 |
|---|---|---|
| `not_too_much` | negative | 重すぎる印象を避ける |
| `not_too_safe` | negative | 無難すぎる印象を避ける |

---

## 5. Semantic Concept分類

### 5.1 Concept Group一覧

| concept_group | 内容 |
|---|---|
| social_appropriateness | 社会的適切性・品位・安全性に関するConcept |
| practical_value | 実用性・機能性に関するConcept |
| emotional_value | 感情・温かさ・祝福に関するConcept |
| special_value | 特別感・記念性・意外性に関するConcept |
| relationship_value | 親密性・関係性に関するConcept |
| identity_value | 相手らしさ・象徴性に関するConcept |
| aesthetic_value | 見た目・センス・印象に関するConcept |
| tone_control | 重さ・無難さなどの調整Concept |

---

## 6. Semantic Concept定義一覧

### 6.1 初期Concept一覧

| concept_code | concept_label | concept_group | 意味 | polarity_default | 関連Feature候補 |
|---|---|---|---|---|---|
| `formal_refined` | 上品・端正 | social_appropriateness | 礼儀正しさ、品位、整った印象を与える意味概念 | positive | formality, brand_appropriateness |
| `safe_classic` | 無難・定番 | social_appropriateness | 失敗しにくさ、受け入れられやすさ、王道感 | positive | safety, formality |
| `prestigious_quality` | 高級・上質 | social_appropriateness | 格、品質、ちゃんとした感、上等さ | positive | brand_appropriateness, formality, story_richness |
| `practical_useful` | 実用・機能 | practical_value | 役立つ、使いやすい、日常的に便利 | positive | safety, brand_appropriateness |
| `emotional_warm` | 温かい気持ち | emotional_value | 感謝、思いやり、心の温度を感じる | positive | emotion, intimacy |
| `special_memorable` | 特別・記憶に残る | special_value | 特別感、印象深さ、記念性 | positive | novelty, emotion, story_richness |
| `surprising_unique` | 意外性・ユニーク | special_value | 珍しさ、ひねり、予想外の魅力 | positive | novelty, symbolic_identity |
| `romantic_affectionate` | 愛情・ロマン | relationship_value | 恋愛的、感情的親密さ、甘さ | positive | emotion, intimacy, symbolic_identity |
| `close_personal` | 親しさ・近さ | relationship_value | 距離感の近さ、身近さ、個人的ニュアンス | positive | intimacy, emotion |
| `symbolic_identity_fit` | その人らしさ | identity_value | 相手らしさ、関係らしさ、意味的一致 | positive | symbolic_identity, story_richness |
| `story_narrative` | ストーリー性 | identity_value | 背景、由来、文脈、語れる意味 | positive | story_richness, symbolic_identity |
| `stylish_aesthetic` | おしゃれ・美意識 | aesthetic_value | センス、デザイン性、洗練された見た目 | positive | novelty, symbolic_identity |
| `cute_soft` | かわいい・柔らかい | aesthetic_value | 愛らしさ、やさしさ、柔和な印象 | positive | emotion, intimacy, novelty |
| `casual_light` | カジュアル・軽さ | tone_control | 気軽さ、堅苦しくなさ、ライトさ | mixed | intimacy, safety, formality |
| `not_too_much` | 重すぎない | tone_control | 過剰さの抑制、気を遣わせすぎない調整概念 | negative | intimacy, emotion, brand_appropriateness |
| `not_too_safe` | 無難すぎない | tone_control | 定番・保守寄りに寄りすぎることへの抑制 | negative | safety, novelty |
| `luxurious_rich` | 豪華・華やか | special_value | 贅沢さ、見栄え、祝祭性 | positive | brand_appropriateness, novelty, emotion |
| `cheerful_positive` | 明るい・前向き | emotional_value | 祝福感、元気、晴れやかさ | positive | emotion, novelty |

---

## 7. Concept詳細定義

## 7.1 `formal_refined`

| 項目 | 内容 |
|---|---|
| concept_label | 上品・端正 |
| concept_group | social_appropriateness |
| polarity_default | positive |
| 定義 | 礼儀正しさ、品位、整った印象を与えるConcept |
| 主な関連Feature | formality, brand_appropriateness |

### 入力例

- 上品なもの
- きちんとしたもの
- 失礼のないもの
- 品のあるギフト
- 端正な印象

### 商品情報例

- 上質な包装
- 老舗ブランド
- フォーマルギフト
- 百貨店品質

### 注意点

`formal_refined` は、単なる高価格を意味しない。  
価格よりも、礼儀・品位・整った印象を重視する。

---

## 7.2 `safe_classic`

| 項目 | 内容 |
|---|---|
| concept_label | 無難・定番 |
| concept_group | social_appropriateness |
| polarity_default | positive |
| 定義 | 失敗しにくさ、受け入れられやすさ、王道感を表すConcept |
| 主な関連Feature | safety, formality |

### 入力例

- 無難なもの
- 定番がいい
- 外さないもの
- 誰にでも喜ばれるもの
- 安心感があるもの

### 商品情報例

- 定番ギフト
- 人気商品
- 王道
- ロングセラー

### 注意点

`safe_classic` は、必ずしも「つまらない」を意味しない。  
特別感が弱いかどうかは、`novelty` や `story_richness` 側で評価する。

---

## 7.3 `prestigious_quality`

| 項目 | 内容 |
|---|---|
| concept_label | 高級・上質 |
| concept_group | social_appropriateness |
| polarity_default | positive |
| 定義 | 格、品質、ちゃんとした感、上等さを表すConcept |
| 主な関連Feature | brand_appropriateness, formality, story_richness |

### 入力例

- 高級感があるもの
- 上質なもの
- ちゃんとしたもの
- 格があるもの
- 安っぽくないもの

### 商品情報例

- 高級
- プレミアム
- 上質素材
- 老舗
- 贈答用

### 注意点

`prestigious_quality` は、文脈によっては過剰になる。  
関係性が近すぎない相手や予算条件と合わせて判断する必要がある。

---

## 7.4 `practical_useful`

| 項目 | 内容 |
|---|---|
| concept_label | 実用・機能 |
| concept_group | practical_value |
| polarity_default | positive |
| 定義 | 役立つ、使いやすい、日常的に便利であるConcept |
| 主な関連Feature | safety, brand_appropriateness |

### 入力例

- 実用的なもの
- 使えるもの
- 普段使いできるもの
- 便利なもの
- 消耗品がいい

### 商品情報例

- 実用品
- 日用品
- 便利グッズ
- 使いやすい
- 毎日使える

### 注意点

`practical_useful` は、Symbolicが低くなりやすい。  
ただし、相手の生活に合っている場合は `symbolic_identity_fit` と組み合わせて意味性を持たせられる。

---

## 7.5 `emotional_warm`

| 項目 | 内容 |
|---|---|
| concept_label | 温かい気持ち |
| concept_group | emotional_value |
| polarity_default | positive |
| 定義 | 感謝、思いやり、心の温度を感じるConcept |
| 主な関連Feature | emotion, intimacy |

### 入力例

- 気持ちが伝わるもの
- 感謝が伝わるもの
- 温かみがあるもの
- 優しい印象
- 心がこもっているもの

### 商品情報例

- 心温まる
- 感謝の気持ち
- メッセージ付き
- 手作り感
- やさしい

### 注意点

`emotional_warm` は、関係性によって重く感じられる場合がある。  
`not_too_much` と組み合わせて調整する場合がある。

---

## 7.6 `special_memorable`

| 項目 | 内容 |
|---|---|
| concept_label | 特別・記憶に残る |
| concept_group | special_value |
| polarity_default | positive |
| 定義 | 特別感、印象深さ、記念性を表すConcept |
| 主な関連Feature | novelty, emotion, story_richness |

### 入力例

- 特別感があるもの
- 記憶に残るもの
- 印象に残るもの
- 記念になるもの
- 普通じゃないもの

### 商品情報例

- 限定
- 記念品
- 特別仕様
- 名入れ
- アニバーサリー

### 注意点

`special_memorable` は、Socialとのバランスが重要である。  
フォーマルな場面では、特別感が強すぎると外す可能性がある。

---

## 7.7 `surprising_unique`

| 項目 | 内容 |
|---|---|
| concept_label | 意外性・ユニーク |
| concept_group | special_value |
| polarity_default | positive |
| 定義 | 珍しさ、ひねり、予想外の魅力を表すConcept |
| 主な関連Feature | novelty, symbolic_identity |

### 入力例

- 意外性があるもの
- ユニークなもの
- 変わったもの
- ひねりがあるもの
- 人とかぶらないもの

### 商品情報例

- ユニーク
- 珍しい
- 個性的
- 話題性
- 変わり種

### 注意点

`surprising_unique` は、safetyを下げる方向に働く場合がある。  
関係性が浅い相手では慎重に扱う。

---

## 7.8 `romantic_affectionate`

| 項目 | 内容 |
|---|---|
| concept_label | 愛情・ロマン |
| concept_group | relationship_value |
| polarity_default | positive |
| 定義 | 恋愛的、感情的親密さ、甘さを表すConcept |
| 主な関連Feature | emotion, intimacy, symbolic_identity |

### 入力例

- 恋人向け
- 愛情が伝わるもの
- ロマンチックなもの
- 記念日に合うもの
- 大切な人に贈るもの

### 商品情報例

- ペア
- ロマンチック
- 愛情
- 記念日
- ハートモチーフ

### 注意点

`romantic_affectionate` は、関係性依存が非常に強い。  
恋人以外の関係では誤適用を避ける。

---

## 7.9 `close_personal`

| 項目 | 内容 |
|---|---|
| concept_label | 親しさ・近さ |
| concept_group | relationship_value |
| polarity_default | positive |
| 定義 | 距離感の近さ、身近さ、個人的ニュアンスを表すConcept |
| 主な関連Feature | intimacy, emotion |

### 入力例

- 親しい人向け
- 友達っぽいもの
- 個人的な感じ
- 距離が近い感じ
- 気軽だけど気持ちがあるもの

### 商品情報例

- パーソナル
- カジュアルギフト
- 身近
- 日常に寄り添う
- 個人向け

### 注意点

`close_personal` は、相手との関係性が浅い場合には不適切になる可能性がある。

---

## 7.10 `symbolic_identity_fit`

| 項目 | 内容 |
|---|---|
| concept_label | その人らしさ |
| concept_group | identity_value |
| polarity_default | positive |
| 定義 | 相手らしさ、関係らしさ、意味的一致を表すConcept |
| 主な関連Feature | symbolic_identity, story_richness |

### 入力例

- その人らしいもの
- 相手に合うもの
- 趣味に合うもの
- 価値観に合うもの
- その人っぽいもの

### 商品情報例

- 趣味向け
- 個性
- ライフスタイル
- こだわり
- ブランド思想

### 注意点

`symbolic_identity_fit` は、相手情報が少ない場合に過剰推定しない。  
十分な入力がない場合は、信頼度を下げて扱う。

---

## 7.11 `story_narrative`

| 項目 | 内容 |
|---|---|
| concept_label | ストーリー性 |
| concept_group | identity_value |
| polarity_default | positive |
| 定義 | 背景、由来、文脈、語れる意味を表すConcept |
| 主な関連Feature | story_richness, symbolic_identity |

### 入力例

- ストーリー性があるもの
- 由来があるもの
- 語れるもの
- 意味があるもの
- 選んだ理由が伝わるもの

### 商品情報例

- 職人
- 産地
- 伝統
- ブランドストーリー
- 作り手の想い

### 注意点

`story_narrative` は、商品説明の情報量に依存しやすい。  
説明情報が少ない商品では低く出る可能性がある。

---

## 7.12 `stylish_aesthetic`

| 項目 | 内容 |
|---|---|
| concept_label | おしゃれ・美意識 |
| concept_group | aesthetic_value |
| polarity_default | positive |
| 定義 | センス、デザイン性、洗練された見た目を表すConcept |
| 主な関連Feature | novelty, symbolic_identity |

### 入力例

- おしゃれなもの
- センスがいいもの
- 洗練されたもの
- 見た目がいいもの
- デザイン性が高いもの

### 商品情報例

- おしゃれ
- デザイン
- 洗練
- スタイリッシュ
- インテリア性

### 注意点

`stylish_aesthetic` は、画像・ビジュアル情報があると精度が上がる。  
MVPではテキスト・タグ中心に推定する。

---

## 7.13 `cute_soft`

| 項目 | 内容 |
|---|---|
| concept_label | かわいい・柔らかい |
| concept_group | aesthetic_value |
| polarity_default | positive |
| 定義 | 愛らしさ、やさしさ、柔和な印象を表すConcept |
| 主な関連Feature | emotion, intimacy, novelty |

### 入力例

- かわいいもの
- やさしい印象
- 柔らかい雰囲気
- 癒されるもの
- 可愛らしいもの

### 商品情報例

- かわいい
- ふんわり
- やさしい
- 癒し
- ナチュラル

### 注意点

`cute_soft` は、相手の属性や関係性によって適切性が変わる。  
ビジネス文脈では過剰評価しない。

---

## 7.14 `casual_light`

| 項目 | 内容 |
|---|---|
| concept_label | カジュアル・軽さ |
| concept_group | tone_control |
| polarity_default | mixed |
| 定義 | 気軽さ、堅苦しくなさ、ライトさを表すConcept |
| 主な関連Feature | intimacy, safety, formality |

### 入力例

- 気軽なもの
- カジュアルなもの
- 重くないもの
- ちょっとしたもの
- ラフなもの

### 商品情報例

- カジュアル
- プチギフト
- 気軽
- ライト
- 日常使い

### 注意点

`casual_light` は文脈により正負が変わる。

| 文脈 | 解釈 |
|---|---|
| 友人へのお礼 | 良い方向 |
| 上司への昇進祝い | 軽すぎる可能性 |
| ちょっとした差し入れ | 適切 |
| フォーマルな内祝い | 不適切の可能性 |

---

## 7.15 `not_too_much`

| 項目 | 内容 |
|---|---|
| concept_label | 重すぎない |
| concept_group | tone_control |
| polarity_default | negative |
| 定義 | 過剰さの抑制、気を遣わせすぎない調整Concept |
| 主な関連Feature | intimacy, emotion, brand_appropriateness |

### 入力例

- 重すぎないもの
- 気を遣わせないもの
- 大げさじゃないもの
- さりげないもの
- ほどよいもの

### 商品情報例

- さりげない
- ちょっとした
- 控えめ
- 気軽
- プチギフト

### 注意点

`not_too_much` は、単に価値が低いことを意味しない。  
「相手に負担を感じさせない」という調整Conceptである。

---

## 7.16 `not_too_safe`

| 項目 | 内容 |
|---|---|
| concept_label | 無難すぎない |
| concept_group | tone_control |
| polarity_default | negative |
| 定義 | 定番・保守寄りに寄りすぎることへの抑制Concept |
| 主な関連Feature | safety, novelty |

### 入力例

- 無難すぎないもの
- ありきたりじゃないもの
- 少し特別感があるもの
- 定番すぎないもの
- ちょっとひねりがあるもの

### 商品情報例

- 限定
- ユニーク
- 個性的
- ひと工夫
- 特別仕様

### 注意点

`not_too_safe` は、safetyをゼロにする意味ではない。  
「安全性を保ちつつ、定番に寄りすぎない」調整Conceptとして扱う。

---

## 7.17 `luxurious_rich`

| 項目 | 内容 |
|---|---|
| concept_label | 豪華・華やか |
| concept_group | special_value |
| polarity_default | positive |
| 定義 | 贅沢さ、見栄え、祝祭性を表すConcept |
| 主な関連Feature | brand_appropriateness, novelty, emotion |

### 入力例

- 豪華なもの
- 華やかなもの
- 見栄えがするもの
- お祝い感があるもの
- 特別な場に合うもの

### 商品情報例

- 豪華
- 華やか
- プレミアム
- ギフトセット
- お祝い

### 注意点

`luxurious_rich` は、予算条件・関係性とのバランスが重要である。  
高すぎる印象は、相手に負担を与える可能性がある。

---

## 7.18 `cheerful_positive`

| 項目 | 内容 |
|---|---|
| concept_label | 明るい・前向き |
| concept_group | emotional_value |
| polarity_default | positive |
| 定義 | 祝福感、元気、晴れやかさを表すConcept |
| 主な関連Feature | emotion, novelty |

### 入力例

- 明るいもの
- 前向きなもの
- 元気が出るもの
- 祝福感があるもの
- 晴れやかな印象

### 商品情報例

- カラフル
- 元気
- 祝い
- ポジティブ
- 明るいデザイン

### 注意点

`cheerful_positive` は、弔事・謝罪・落ち着いた場面では不適切になる可能性がある。  
Occasionとの組み合わせで制御する。

---

## 8. Semantic ConceptとFeatureの関係

### 8.1 基本関係

Semantic Conceptは、Feature値を生成するための入力である。

```text
Semantic Concept
↓
Feature Rule
↓
Feature Value
```

---

### 8.2 関連Feature候補の意味

本ドキュメントに記載する関連Feature候補は、Conceptが主に影響しやすいFeatureの候補である。

ただし、具体的な影響量・重み・補正係数は、本ドキュメントでは定義しない。

| 定義対象 | 管理ドキュメント |
|---|---|
| Conceptの意味 | Semantic Concept定義書 |
| Concept抽出ルール | Semanticルール定義書 |
| Concept → Feature重み | Featureルール定義書 |
| Feature比較 | Matching定義書 |

---

### 8.3 ConceptとFeatureの対応イメージ

| Concept | 主な影響Feature |
|---|---|
| `formal_refined` | formality, brand_appropriateness |
| `safe_classic` | safety |
| `emotional_warm` | emotion, intimacy |
| `special_memorable` | novelty, emotion, story_richness |
| `symbolic_identity_fit` | symbolic_identity, story_richness |
| `story_narrative` | story_richness |
| `not_too_much` | intimacy, emotionの抑制 |
| `not_too_safe` | safetyの抑制、noveltyの補助 |

---

## 9. Semantic Conceptとpolarity

### 9.1 positive

`positive` は、対象Featureを強める方向で作用する。

例：

```text
「上品なもの」
↓
formal_refined
↓
formality / brand_appropriateness を高める
```

---

### 9.2 negative

`negative` は、対象Featureを抑制または回避する方向で作用する。

例：

```text
「無難すぎないもの」
↓
not_too_safe
↓
safetyに寄りすぎる状態を抑制し、noveltyを補助する
```

---

### 9.3 mixed

`mixed` は、文脈によって作用方向が変わる。

例：

```text
「カジュアルなもの」
```

| 文脈 | 解釈 |
|---|---|
| 親しい友人へのお礼 | positive |
| 上司への正式なお祝い | negative寄り |
| ちょっとした差し入れ | positive |

---

## 10. Semantic Conceptと入力種別

### 10.1 好み条件

好み条件に含まれるConceptは、原則としてFeatureを強める方向に作用する。

例：

```text
「特別感があるものがいい」
↓
special_memorable
↓
novelty / emotion / story_richness を高める
```

---

### 10.2 避けたい条件

避けたい条件に含まれるConceptは、該当ConceptのFeature寄与を抑制する。

例：

```text
「重すぎるものは避けたい」
↓
not_too_much
↓
intimacy / emotion の過剰寄与を抑制する
```

---

### 10.3 NG条件

NG条件は、Semantic Conceptではなく、原則としてハードフィルタに分離する。

例：

| 入力 | 扱い |
|---|---|
| アルコールはNG | hard_filter |
| 香りが強いものはNG | hard_filter または avoid condition |
| 予算は5,000円まで | budget_condition |
| 生ものは避けたい | hard_filter |

---

### 10.4 商品情報

商品情報から抽出されるConceptは、Item Feature生成に利用する。

例：

```text
商品説明：「老舗ブランドの上質なギフトセット」
↓
formal_refined
prestigious_quality
safe_classic
```

---

## 11. Semantic Conceptの管理

### 11.1 管理単位

Semantic Concept定義は、`semantic_config_version` に紐づけて管理する。

理由は、Semantic Conceptが「意味の作り方」の中核要素であるためである。

---

### 11.2 変更ルール

| 変更種別 | MVPでの扱い | 注意点 |
|---|---|---|
| Concept追加 | 可能 | Featureルールとの整合が必要 |
| Concept削除 | 原則禁止 | 過去runの再現性に影響 |
| concept_code変更 | 禁止 | DB・ログ・ルール参照が壊れる |
| concept_label変更 | 影響確認のうえ可能 | UI表示・説明文に影響 |
| description変更 | 可能 | ただし意味変更を伴う場合はversion更新 |
| polarity_default変更 | 原則慎重 | Feature生成結果に影響 |
| group変更 | 可能 | 分析・管理分類の変更として扱う |

---

### 11.3 追加判断基準

新しいSemantic Conceptを追加する場合、以下を満たすこと。

| 判断基準 | 内容 |
|---|---|
| 独立性 | 既存Conceptで表現できない |
| 利用頻度 | ユーザー入力・商品情報に一定頻度で現れる |
| Feature影響 | どのFeatureに効くか説明できる |
| 説明可能性 | 人間が意味を理解できる |
| 運用可能性 | Semanticルール・Featureルールに落とせる |

---

## 12. DB・実装上の扱い

### 12.1 論理データ表現

Semantic Concept定義は、論理的には以下の項目を持つ。

| 項目 | 内容 |
|---|---|
| concept_code | Conceptの物理名 |
| concept_label | 日本語表示名 |
| concept_group | Concept分類 |
| description | 意味定義 |
| polarity_default | 初期極性 |
| is_active | 利用可否 |
| display_order | 表示順 |
| semantic_config_version_id | 定義バージョン |

---

### 12.2 Concept抽出結果

ユーザー入力や商品情報から抽出されたConceptは、論理的には以下のように保持する。

| 項目 | 内容 |
|---|---|
| target_type | user / item |
| target_id | user_request / item等の識別子 |
| source_type | input_text / item_name / item_description / review / tag等 |
| concept_code | 抽出されたConcept |
| polarity | 実際に適用された極性 |
| confidence | 抽出信頼度 |
| evidence_text | 抽出根拠テキスト |
| semantic_config_version_id | 使用した意味定義バージョン |
| generated_at | 生成日時 |

---

### 12.3 evidence_text

`evidence_text` は、Concept抽出の根拠となった入力断片である。

例：

| evidence_text | concept_code |
|---|---|
| 上品なもの | `formal_refined` |
| 無難すぎない | `not_too_safe` |
| 心温まる贈り物 | `emotional_warm` |
| 職人が作った | `story_narrative` |

MVPでは、evidence_textは簡易保持でよい。  
ただし、後続の説明生成・デバッグ・人手評価に有用であるため、保持を推奨する。

---

## 13. Semantic Concept品質観点

### 13.1 レビュー観点

| 観点 | 確認内容 |
|---|---|
| 意味の明確性 | Conceptの意味が曖昧でないか |
| Feature接続性 | どのFeatureに効くか説明できるか |
| 重複排除 | 既存Conceptと意味が重複していないか |
| 入力適合性 | 実際のユーザー入力・商品文言に現れるか |
| 説明可能性 | 推薦理由として人間に説明できるか |
| 極性妥当性 | polarity_defaultが自然か |

---

### 13.2 よくある問題

| 問題 | 内容 | 対応 |
|---|---|---|
| Conceptが細かすぎる | 類似Conceptが乱立する | 既存Conceptへ統合 |
| Conceptが広すぎる | Feature変換が曖昧になる | Concept分割 |
| positive過多 | 何でも高評価になる | negative / mixed Conceptを活用 |
| 商品情報依存が強い | 商品説明が薄いと抽出できない | タグ・カテゴリも併用 |
| relationship依存が強い | 同じConceptでも文脈で意味が変わる | Featureルール側でpair_ruleを使う |

---

## 14. Semantic Conceptで扱わないもの

### 14.1 除外対象

| 対象 | 理由 | 管理先 |
|---|---|---|
| 価格 | 意味概念ではなく条件 | budget_condition |
| 在庫 | 商品利用可能性 | Item Data / Availability |
| 配送 | EC機能 | 将来拡張 |
| レビュー点数 | 人気・信頼指標 | popularity_score |
| レビュー件数 | 人気・信頼指標 | popularity_score |
| NG条件 | 絶対除外条件 | hard_filter |
| final_score | 順位決定結果 | Ranking |
| risk_score | リスク補正 | Ranking |

---

## 15. MVPでの扱い

### 15.1 MVP対象

| 項目 | 方針 |
|---|---|
| 初期Concept数 | 18個 |
| Concept抽出 | ルールベース + LLM補助を許容 |
| User入力 | 好み条件・避けたい条件・自由入力から抽出 |
| Item情報 | 商品名・説明・カテゴリ・タグ・レビューから抽出 |
| polarity | positive / negative / mixed を扱う |
| evidence_text | 簡易保持を推奨 |

---

### 15.2 MVP対象外

| 項目 | 理由 |
|---|---|
| 大量Concept追加 | 運用・評価が難しくなる |
| 自動Concept学習 | 学習データ不足 |
| 個人別Concept最適化 | 認証・履歴管理が前提 |
| 高度な同義語辞書 | 初期検証では過剰 |
| 多言語対応 | MVP範囲外 |

---

## 16. 後続成果物への引き継ぎ

### 16.1 Featureルール定義書への引き継ぎ

Featureルール定義書では、以下を定義する。

| 引き継ぎ項目 | 内容 |
|---|---|
| concept_code | Feature変換の入力キー |
| polarity | Featureへの作用方向 |
| related_feature_candidates | 重み定義の候補 |
| concept_group | ルール整理単位 |

---

### 16.2 Semanticルール定義書への引き継ぎ

Semanticルール定義書では、以下を定義する。

| 引き継ぎ項目 | 内容 |
|---|---|
| concept_code | 抽出先Concept |
| concept_label | 表示・確認用ラベル |
| description | 抽出判断の意味基準 |
| 入力例 | keyword / phrase / LLM判定例 |
| polarity_default | 初期極性 |

---

## 17. まとめ

Semantic Conceptは、自然言語とFeatureの間に置く中間概念である。

```text
User Input / Item Data
↓
Semantic Concept
↓
Feature
↓
Gift Meaning Space
↓
Matching
↓
Ranking
```

本サービスでは、Semantic Conceptにより以下を実現する。

- 自然言語の意味を構造化する
- Feature生成ルールを整理しやすくする
- 推薦理由を説明しやすくする
- User MeaningとItem Meaningを同じ意味体系で扱う

MVPでは、初期Conceptを18個で開始し、Feature定義・Featureルール・Semanticルールと整合させながら運用する。