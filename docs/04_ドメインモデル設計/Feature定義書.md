# Feature定義書

## 1. 概要

### 1.1 目的

本ドキュメントは、ギフトレコメンドサービスにおける `Feature` を定義する。

Featureは、Gift Meaningを構成する最小単位であり、ユーザーの贈答意図および商品が持つ意味を数値化するための共通次元である。

---

### 1.2 本ドキュメントの位置づけ

本ドキュメントは、以下の成果物の前提となる。

| 成果物                   | 本ドキュメントとの関係                          |
| ------------------------ | ----------------------------------------------- |
| Gift Meaning Space定義書 | FeatureをSocial / Symbolicへ射影する前提        |
| Semantic Concept定義書   | Semantic Conceptが影響するFeatureを定義する前提 |
| Featureルール定義書      | Context / ConceptからFeature値を生成する前提    |
| Semanticルール定義書     | 入力文をSemantic Conceptへ変換する前提          |
| Matching定義書           | User FeatureとItem Featureを比較する前提        |
| Ranking定義書            | context_score等を利用する前提                   |

---

### 1.3 基本方針

- Featureは、Gift Meaningを構成する最小単位とする
- MVPではFeatureを8次元固定とする
- Featureは `Social` 系と `Symbolic` 系に分類する
- User MeaningとItem Meaningは、同じFeature定義に基づいて表現する
- Feature値は、原則として `0.0〜1.0` の範囲で扱う
- Feature定義とFeature値生成ルールを混同しない

---

## 2. Featureの定義

### 2.1 Featureとは

Featureとは、ギフトの意味的価値を構成する数値次元である。

本サービスでは、以下をFeatureで表現する。

- きちんと感
- 外しにくさ
- ブランド・品位の適切さ
- 感情の伝わりやすさ
- 特別感
- 親密性
- 相手らしさ・象徴性
- ストーリー性

---

### 2.2 Featureの役割

Featureは、以下の処理で利用する。

| 処理                   | Featureの役割                           |
| ---------------------- | --------------------------------------- |
| User Meaning生成       | ユーザー入力をFeatureベクトルへ変換する |
| Item Meaning生成       | 商品情報をFeatureベクトルへ変換する     |
| Gift Meaning Space射影 | FeatureをSocial / Symbolicへ集約する    |
| Matching               | User FeatureとItem Featureを比較する    |
| Explanation            | なぜおすすめかを説明する材料にする      |
| Monitoring             | Feature分布を監視する                   |

---

### 2.3 FeatureとMeaningの違い

| 概念               | 内容                                 |
| ------------------ | ------------------------------------ |
| Feature            | Gift Meaningを構成する個別の数値次元 |
| Meaning            | Featureを統合した意味表現            |
| Gift Meaning Space | Meaningを比較・可視化する空間        |

```text
Feature = 意味の部品
Meaning = Featureを統合した意味表現
Gift Meaning Space = Meaningを配置する空間
```

---

## 3. Feature構成

### 3.1 Feature分類

Featureは、以下の2分類で構成する。

| 分類     | 内容                       | Feature数 |
| -------- | -------------------------- | --------: |
| Social   | 社会的適合性・安全性を表す |         3 |
| Symbolic | 感情・特別感・意味性を表す |         5 |

---

### 3.2 Feature一覧

| 分類     | feature_code            | 論理名          | 概要                                     |
| -------- | ----------------------- | --------------- | ---------------------------------------- |
| Social   | `formality`             | 儀礼性          | きちんと感・儀礼性の強さ                 |
| Social   | `safety`                | 安全性          | 外しにくさ・無難さ                       |
| Social   | `brand_appropriateness` | ブランド適切性  | ブランド格・品位の適切さ                 |
| Symbolic | `emotion`               | 感情表現性      | 感情を表現しやすい度合い                 |
| Symbolic | `novelty`               | 新規性 / 特別感 | 特別感・目新しさ                         |
| Symbolic | `intimacy`              | 親密性          | 親密な関係に向く度合い                   |
| Symbolic | `symbolic_identity`     | 象徴性          | ブランド・文化・由来など象徴的意味の強さ |
| Symbolic | `story_richness`        | ストーリー性    | 語れる背景や意味の豊かさ                 |

---

### 3.3 Feature Vector

Feature Vectorは、以下の順序で定義する。

```text
feature_vector = [
  formality,
  safety,
  brand_appropriateness,
  emotion,
  novelty,
  intimacy,
  symbolic_identity,
  story_richness
]
```

---

### 3.4 Feature順序の固定

Feature Vectorの順序は固定する。

理由は、以下の処理で同じ順序が前提になるためである。

- DB保存
- Embedding以外のFeature比較
- Matching計算
- 分布監視
- オフライン評価
- モデルバージョン管理

---

## 4. Feature値定義

### 4.1 値域

各Feature値は、原則として以下の範囲で扱う。

```text
0.0 <= feature_value <= 1.0
```

|  値 | 意味                   |
| --: | ---------------------- |
| 0.0 | その性質がほとんどない |
| 0.5 | 中立・標準的           |
| 1.0 | その性質が非常に強い   |

---

### 4.2 値の解釈

Feature値は、「良い / 悪い」を表すものではない。  
あくまで、その性質がどれだけ強いかを表す。

例：

| Feature   | 高い場合         | 注意点                               |
| --------- | ---------------- | ------------------------------------ |
| safety    | 外しにくい       | つまらないとは限らない               |
| novelty   | 特別感がある     | 必ずしも適切とは限らない             |
| intimacy  | 親密性が高い     | 関係性によっては重すぎる可能性がある |
| formality | きちんとしている | 冷たい印象になる場合もある           |

---

### 4.3 raw / normalized

Feature値は、以下の2段階で扱う。

| 種別       | 内容                        | 用途                   |
| ---------- | --------------------------- | ---------------------- |
| raw        | ルール・推定直後のFeature値 | 推定結果の保持・分析   |
| normalized | 0〜1へ正規化したFeature値   | Matching / 射影 / 評価 |

---

### 4.4 User Feature / Item Feature

同じFeature定義を、User MeaningとItem Meaningの両方に適用する。

| 対象         | 内容                                    |
| ------------ | --------------------------------------- |
| User Feature | ユーザーの贈答意図をFeatureで表したもの |
| Item Feature | 商品が持つ意味をFeatureで表したもの     |

```text
User Feature × Item Feature = Matching
```

---

## 5. Social Feature定義

## 5.1 formality

### 基本情報

| 項目         | 内容                                   |
| ------------ | -------------------------------------- |
| feature_code | `formality`                            |
| 論理名       | 儀礼性                                 |
| 分類         | Social                                 |
| 意味         | きちんと感・フォーマルさ・儀礼性の強さ |

---

### 定義

`formality` は、ギフトがどれだけ礼儀正しく、フォーマルな場面に適しているかを表すFeatureである。

---

### 値が高い状態

| 観点     | 例                                                 |
| -------- | -------------------------------------------------- |
| 場面     | 上司・取引先・目上の人への贈答に向く               |
| 印象     | きちんとしている、失礼がない、品がある             |
| 商品傾向 | 高級菓子、格式あるブランド、きちんと包装された商品 |
| 文脈     | 昇進祝い、内祝い、フォーマルなお礼                 |

---

### 値が低い状態

| 観点     | 例                                             |
| -------- | ---------------------------------------------- |
| 場面     | カジュアルな友人関係・気軽な贈り物             |
| 印象     | ラフ、気軽、遊び心がある                       |
| 商品傾向 | ネタ系商品、カジュアル雑貨、遊び要素が強い商品 |

---

### 注意点

`formality` が高いことは、必ずしも良いことではない。  
恋人・親しい友人などでは、formalityが高すぎると距離感が出る場合がある。

---

## 5.2 safety

### 基本情報

| 項目         | 内容                             |
| ------------ | -------------------------------- |
| feature_code | `safety`                         |
| 論理名       | 安全性                           |
| 分類         | Social                           |
| 意味         | 外しにくさ・無難さ・失敗しにくさ |

---

### 定義

`safety` は、ギフトとして失敗しにくく、相手に受け入れられやすい度合いを表すFeatureである。

---

### 値が高い状態

| 観点     | 例                                               |
| -------- | ------------------------------------------------ |
| 印象     | 無難、万人受け、安心感がある                     |
| 商品傾向 | 定番商品、レビュー評価が安定している商品、消耗品 |
| 文脈     | お礼、職場、関係性が浅い相手                     |
| リスク   | 好みのズレが起きにくい                           |

---

### 値が低い状態

| 観点     | 例                                               |
| -------- | ------------------------------------------------ |
| 印象     | 好みが分かれる、攻めている、個性的               |
| 商品傾向 | 強いデザイン性、香りが強い商品、趣味性の高い商品 |
| リスク   | 相手に合わない可能性がある                       |

---

### 注意点

`safety` が高い商品は、必ずしも「つまらない商品」ではない。  
本サービスでは、safetyは「失敗しにくさ」として扱い、特別感の有無は `novelty` や `story_richness` で表現する。

---

## 5.3 brand_appropriateness

### 基本情報

| 項目         | 内容                               |
| ------------ | ---------------------------------- |
| feature_code | `brand_appropriateness`            |
| 論理名       | ブランド適切性                     |
| 分類         | Social                             |
| 意味         | ブランド格・品位・場面との釣り合い |

---

### 定義

`brand_appropriateness` は、商品やブランドの格・品位・印象が、贈答文脈に対して適切かを表すFeatureである。

---

### 値が高い状態

| 観点     | 例                                       |
| -------- | ---------------------------------------- |
| 印象     | 品位がある、安っぽく見えない、場面に合う |
| 商品傾向 | 信頼感のあるブランド、ギフト向きブランド |
| 文脈     | 上司、取引先、フォーマルな祝い事         |
| 価格感   | 高すぎず低すぎず、関係性に合っている     |

---

### 値が低い状態

| 観点     | 例                                         |
| -------- | ------------------------------------------ |
| 印象     | 場面に対して軽すぎる、安っぽい、過剰に高級 |
| 商品傾向 | 贈答文脈とブランド印象が合わない商品       |
| リスク   | 相手に違和感を与える可能性がある           |

---

### 注意点

`brand_appropriateness` は、単純なブランド知名度ではない。  
「有名ブランドか」ではなく、「その関係性・用途に対して適切か」を表す。

---

## 6. Symbolic Feature定義

## 6.1 emotion

### 基本情報

| 項目         | 内容                     |
| ------------ | ------------------------ |
| feature_code | `emotion`                |
| 論理名       | 感情表現性               |
| 分類         | Symbolic                 |
| 意味         | 感情を表現しやすい度合い |

---

### 定義

`emotion` は、ギフトを通じて感謝・愛情・応援・祝福などの感情を伝えやすい度合いを表すFeatureである。

---

### 値が高い状態

| 観点     | 例                                               |
| -------- | ------------------------------------------------ |
| 印象     | 気持ちが伝わる、温かい、心がこもっている         |
| 商品傾向 | メッセージ性のある商品、記念性のある商品         |
| 文脈     | 誕生日、記念日、お礼、応援                       |
| 表現     | 「ありがとう」「おめでとう」「大切に思っている」 |

---

### 値が低い状態

| 観点     | 例                                         |
| -------- | ------------------------------------------ |
| 印象     | 事務的、機能的、無機質                     |
| 商品傾向 | 実用品中心、消耗品中心、意味づけが弱い商品 |
| 文脈     | 感情表現を抑えたい場面                     |

---

### 注意点

`emotion` が高すぎると、関係性によっては重く感じられる可能性がある。  
そのため、`intimacy` や `formality` と組み合わせて判断する。

---

## 6.2 novelty

### 基本情報

| 項目         | 内容                           |
| ------------ | ------------------------------ |
| feature_code | `novelty`                      |
| 論理名       | 新規性 / 特別感                |
| 分類         | Symbolic                       |
| 意味         | 目新しさ・印象の強さ・非日常感 |

---

### 定義

`novelty` は、ギフトがどれだけ新鮮で、印象に残り、特別感を持つかを表すFeatureである。

---

### 値が高い状態

| 観点     | 例                                           |
| -------- | -------------------------------------------- |
| 印象     | 珍しい、特別、印象に残る                     |
| 商品傾向 | 限定品、体験型ギフト、デザイン性が高い商品   |
| 文脈     | 誕生日、記念日、サプライズ                   |
| 効果     | 「自分では選ばないが嬉しい」体験を作りやすい |

---

### 値が低い状態

| 観点     | 例                             |
| -------- | ------------------------------ |
| 印象     | 定番、予想しやすい、無難       |
| 商品傾向 | 一般的な定番ギフト、日常消耗品 |
| 効果     | 驚きは少ないが安心感はある     |

---

### 注意点

`novelty` は、必ずしも高ければよいわけではない。  
関係性が浅い相手やフォーマルな場面では、noveltyが高すぎると外すリスクがある。

---

## 6.3 intimacy

### 基本情報

| 項目         | 内容                   |
| ------------ | ---------------------- |
| feature_code | `intimacy`             |
| 論理名       | 親密性                 |
| 分類         | Symbolic               |
| 意味         | 親密な関係に向く度合い |

---

### 定義

`intimacy` は、ギフトが相手との近い関係性や個人的な距離感を表現する度合いを表すFeatureである。

---

### 値が高い状態

| 観点     | 例                                         |
| -------- | ------------------------------------------ |
| 関係性   | 恋人、家族、親友                           |
| 印象     | 個人的、親しい、距離が近い                 |
| 商品傾向 | 身につけるもの、個人の好みに深く関わるもの |
| 文脈     | 誕生日、記念日、個人的なお祝い             |

---

### 値が低い状態

| 観点     | 例                                 |
| -------- | ---------------------------------- |
| 関係性   | 上司、取引先、知人                 |
| 印象     | 距離を保つ、ビジネスライク、一般的 |
| 商品傾向 | 消耗品、食品、職場向けギフト       |

---

### 注意点

`intimacy` が高い商品は、相手との関係性によって評価が大きく変わる。  
恋人には適切でも、上司や取引先には不適切になる可能性がある。

---

## 6.4 symbolic_identity

### 基本情報

| 項目         | 内容                                                 |
| ------------ | ---------------------------------------------------- |
| feature_code | `symbolic_identity`                                  |
| 論理名       | 象徴性                                               |
| 分類         | Symbolic                                             |
| 意味         | 相手らしさ・ブランド・文化・由来など象徴的意味の強さ |

---

### 定義

`symbolic_identity` は、ギフトが相手らしさ、価値観、趣味、ブランドの意味、文化的背景などを象徴できる度合いを表すFeatureである。

---

### 値が高い状態

| 観点     | 例                                             |
| -------- | ---------------------------------------------- |
| 印象     | その人らしい、意味がある、象徴的               |
| 商品傾向 | 趣味・価値観に合う商品、ブランド思想が強い商品 |
| 文脈     | 相手の個性を反映した贈り物                     |
| 効果     | 「自分のことを考えて選んでくれた」と感じやすい |

---

### 値が低い状態

| 観点     | 例                                     |
| -------- | -------------------------------------- |
| 印象     | 一般的、誰にでも当てはまる             |
| 商品傾向 | 汎用的な定番商品、個性反映が少ない商品 |
| 効果     | 個別性は弱いが安全性は高い場合がある   |

---

### 注意点

`symbolic_identity` は、相手情報の不足に弱い。  
ユーザー入力や商品情報から相手らしさを十分に推定できない場合は、過度に高く評価しない。

---

## 6.5 story_richness

### 基本情報

| 項目         | 内容                     |
| ------------ | ------------------------ |
| feature_code | `story_richness`         |
| 論理名       | ストーリー性             |
| 分類         | Symbolic                 |
| 意味         | 語れる背景や意味の豊かさ |

---

### 定義

`story_richness` は、ギフトに込められた理由・背景・由来・文脈を説明しやすい度合いを表すFeatureである。

---

### 値が高い状態

| 観点     | 例                                                 |
| -------- | -------------------------------------------------- |
| 印象     | 理由がある、語れる、背景がある                     |
| 商品傾向 | 職人性、産地、限定性、ブランドストーリーがある商品 |
| 文脈     | 記念日、節目のお祝い、思い出に関係する贈り物       |
| 効果     | 「なぜこれを選んだのか」を説明しやすい             |

---

### 値が低い状態

| 観点     | 例                                     |
| -------- | -------------------------------------- |
| 印象     | 実用的、説明不要、背景が弱い           |
| 商品傾向 | 汎用消耗品、無難な定番商品             |
| 効果     | 受け取りやすいが、意味の深さは出にくい |

---

### 注意点

`story_richness` は、商品説明やブランド背景の情報量に依存しやすい。  
情報が少ない商品では、実際にストーリー性があっても低く推定される可能性がある。

---

## 7. Feature間の関係

### 7.1 Social系Featureの関係

| Feature               | 近い概念              | 違い                                                          |
| --------------------- | --------------------- | ------------------------------------------------------------- |
| formality             | safety                | formalityは礼儀・格式、safetyは外しにくさ                     |
| safety                | brand_appropriateness | safetyは失敗しにくさ、brand_appropriatenessは場面との釣り合い |
| brand_appropriateness | formality             | brand_appropriatenessはブランド・価格・品位の適切性を含む     |

---

### 7.2 Symbolic系Featureの関係

| Feature           | 近い概念          | 違い                                                            |
| ----------------- | ----------------- | --------------------------------------------------------------- |
| emotion           | intimacy          | emotionは感情表現、intimacyは関係性の近さ                       |
| novelty           | story_richness    | noveltyは目新しさ、story_richnessは背景の語りやすさ             |
| symbolic_identity | story_richness    | symbolic_identityは相手らしさ、story_richnessは選定理由の豊かさ |
| novelty           | symbolic_identity | noveltyは新鮮さ、symbolic_identityは意味の象徴性                |

---

### 7.3 代表的な組み合わせ

| 組み合わせ                                   | 意味                               |
| -------------------------------------------- | ---------------------------------- |
| high safety + low novelty                    | 無難で失敗しにくい                 |
| high novelty + low safety                    | 攻めたギフト                       |
| high formality + high brand_appropriateness  | フォーマルで品位がある             |
| high emotion + high intimacy                 | 気持ちが伝わる親密なギフト         |
| high symbolic_identity + high story_richness | 相手らしく、語れる意味があるギフト |

---

## 8. FeatureとSocial / Symbolicの関係

### 8.1 Social算出対象

Socialは、以下のFeatureを集約して算出する。

```text
Social = aggregate(
  formality,
  safety,
  brand_appropriateness
)
```

---

### 8.2 Symbolic算出対象

Symbolicは、以下のFeatureを集約して算出する。

```text
Symbolic = aggregate(
  emotion,
  novelty,
  intimacy,
  symbolic_identity,
  story_richness
)
```

---

### 8.3 集約方式

FeatureからSocial / Symbolicへの集約方式は、本ドキュメントでは詳細定義しない。  
集約方式・重み・正規化は、Gift Meaning Space定義書およびFeatureルール定義書で定義する。

---

## 9. Feature生成における入力源

### 9.1 User Featureの入力源

User Featureは、以下の情報から生成される。

| 入力源       | 主に影響するFeature                                   |
| ------------ | ----------------------------------------------------- |
| Relationship | formality / safety / brand_appropriateness / intimacy |
| Occasion     | formality / safety / emotion / novelty                |
| 好み条件     | 該当するFeature全般                                   |
| 避けたい条件 | 該当するFeatureの抑制・回避                           |
| NG条件       | Featureではなくハードフィルタに分離                   |
| 予算条件     | Featureではなくハードフィルタに分離                   |

---

### 9.2 Item Featureの入力源

Item Featureは、以下の情報から生成される。

| 入力源       | 主に影響するFeature                          |
| ------------ | -------------------------------------------- |
| 商品名       | novelty / symbolic_identity / story_richness |
| 商品説明     | emotion / story_richness / symbolic_identity |
| 商品カテゴリ | safety / formality / intimacy                |
| 商品タグ     | 該当するFeature全般                          |
| ブランド情報 | brand_appropriateness / symbolic_identity    |
| レビュー情報 | safety / emotion                             |
| 価格情報     | brand_appropriateness / formality            |
| 画像情報     | MVPでは必須対象外                            |

---

## 10. Featureで扱わないもの

### 10.1 Featureに含めない概念

以下はFeatureとしては定義しない。

| 概念           | 扱い                                  |
| -------------- | ------------------------------------- |
| 価格           | ハードフィルタ・価格条件として扱う    |
| 在庫           | 商品利用可能性として扱う              |
| 配送日         | EC連携・将来拡張として扱う            |
| レビュー評価点 | popularity / safety補助情報として扱う |
| レビュー件数   | popularity補助情報として扱う          |
| NG条件         | ハードフィルタとして扱う              |
| 人気度         | Ranking側のpopularity_scoreとして扱う |
| 失敗リスク     | Ranking側のrisk_scoreとして扱う       |
| conformity     | MVPではFeature対象外                  |

---

### 10.2 FeatureとRanking要素の分離

Featureは、意味を表すための次元である。  
最終順位を直接決めるための補正値ではない。

| 項目             | 管理領域                |
| ---------------- | ----------------------- |
| Feature          | semantic_config_version |
| context_score    | model_version           |
| popularity_score | model_version           |
| risk_score       | model_version           |
| final_score      | model_version           |

---

## 11. Feature定義の管理

### 11.1 管理単位

Feature定義は、`semantic_config_version` に紐づけて管理する。

理由は、Featureは「意味の作り方」に該当するためである。

---

### 11.2 変更ルール

MVPではFeatureの追加・削除は行わない。

| 変更種別         | MVPでの扱い                 |
| ---------------- | --------------------------- |
| Feature追加      | 原則禁止                    |
| Feature削除      | 禁止                        |
| feature_code変更 | 禁止                        |
| 論理名変更       | 原則禁止                    |
| 説明文修正       | 影響確認のうえ可能          |
| 例示追加         | 可能                        |
| 重み変更         | Featureルール定義書側で管理 |

---

### 11.3 feature_code命名規則

| 項目   | ルール                       |
| ------ | ---------------------------- |
| 形式   | snake_case                   |
| 言語   | 英語                         |
| 数     | 単数形                       |
| 安定性 | 一度定義したら原則変更しない |

---

## 12. DB・実装上の扱い

### 12.1 論理データ表現

Feature定義は、論理的には以下のような構造で管理する。

| 項目                       | 内容              |
| -------------------------- | ----------------- |
| feature_code               | Featureの物理名   |
| feature_label              | 日本語表示名      |
| feature_group              | Social / Symbolic |
| description                | 定義              |
| value_min                  | 最小値            |
| value_max                  | 最大値            |
| display_order              | 表示順            |
| is_active                  | 利用可否          |
| semantic_config_version_id | 定義バージョン    |

---

### 12.2 Feature値表現

User Feature / Item Featureは、論理的には以下を保持する。

| 項目                       | 内容                             |
| -------------------------- | -------------------------------- |
| target_type                | user / item                      |
| target_id                  | user_request / item等の識別子    |
| feature_code               | Feature種別                      |
| raw_value                  | 推定直後の値                     |
| normalized_value           | 正規化後の値                     |
| semantic_config_version_id | 生成に使用した意味定義バージョン |
| generated_at               | 生成日時                         |

---

### 12.3 物理実装方針

物理実装では、以下のいずれも許容する。

| 方式   | 内容                   | 備考                    |
| ------ | ---------------------- | ----------------------- |
| 縦持ち | feature_codeごとに1行  | 分析・拡張に強い        |
| 横持ち | 8Featureをカラムで保持 | 計算・参照が簡単        |
| JSON   | FeatureをJSONで保持    | MVPでは簡易実装しやすい |

MVPでは、実装容易性を優先し、JSONまたは横持ちも許容する。  
ただし、Feature定義そのものは正本として管理する。

---

## 13. Feature品質観点

### 13.1 レビュー観点

Feature値を評価する際は、以下を確認する。

| 観点       | 確認内容                                    |
| ---------- | ------------------------------------------- |
| 解釈妥当性 | Feature値が人間の感覚と大きくズレていないか |
| 分布妥当性 | すべての値が0.5付近に集中していないか       |
| 差別化     | Featureごとの値に意味ある差が出ているか     |
| 相関過多   | 複数Featureが常に同じ値になっていないか     |
| 説明可能性 | なぜその値になったか説明できるか            |

---

### 13.2 よくある問題

| 問題                  | 内容                           | 対応                          |
| --------------------- | ------------------------------ | ----------------------------- |
| safety過大            | 何でも無難判定になる           | concept / contextルール見直し |
| novelty過大           | 目新しい商品が過剰評価される   | safetyとのバランス確認        |
| intimacy過大          | 関係性が浅くても親密判定になる | relationship rule見直し       |
| symbolic_identity不足 | 相手らしさが出ない             | 入力情報・商品情報の拡充      |
| story_richness不足    | 説明理由が弱い                 | 商品説明・ブランド情報の活用  |

---

## 14. MVPでの扱い

### 14.1 MVP対象

| 項目         | 方針                     |
| ------------ | ------------------------ |
| Feature数    | 8次元固定                |
| 値域         | 0.0〜1.0                 |
| User Feature | OLで生成                 |
| Item Feature | BTで事前生成             |
| Feature比較  | Matchingで利用           |
| Feature表示  | 必要に応じて説明用に利用 |

---

### 14.2 MVP対象外

| 項目                | 理由                           |
| ------------------- | ------------------------------ |
| Feature追加         | 検証軸がブレるため             |
| 自動Feature学習     | 学習データ不足のため           |
| 複雑なFeature分解   | 初期検証には過剰なため         |
| 画像由来Feature推定 | 初期MVPでは対象外              |
| 個人別Feature最適化 | 認証・履歴管理が前提になるため |

---

## 15. 今後の詳細化対象

| 成果物                 | 詳細化内容                                              |
| ---------------------- | ------------------------------------------------------- |
| Featureルール定義書    | Context / Semantic ConceptからFeature値を生成するルール |
| Semantic Concept定義書 | Featureへ影響する中間概念一覧                           |
| Semanticルール定義書   | 入力文・商品情報からSemantic Conceptを推定するルール    |
| Matching定義書         | Feature距離・一致度・social_match / symbolic_match      |
| 分布監視設計書         | Feature値の分布監視・異常検知                           |
| オフライン評価設計書   | Feature妥当性・推薦品質評価                             |

---

## 16. まとめ

Featureは、Gift Meaningを数値化するための最小単位である。

```text
Natural Language / Context / Item Data
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

MVPでは、Featureを以下の8次元で固定する。

```text
Social:
- formality
- safety
- brand_appropriateness

Symbolic:
- emotion
- novelty
- intimacy
- symbolic_identity
- story_richness
```

Featureは「意味の部品」であり、最終順位や人気補正とは分離して管理する。  
Feature定義は `semantic_config_version` に紐づけ、Feature値生成ルール・正規化・射影ルールと整合するように管理する。
