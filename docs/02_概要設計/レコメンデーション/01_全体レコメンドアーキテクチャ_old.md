# Gift Recommendation Service

## 全体レコメンドアーキテクチャ図（最終系の大枠）

まず全体像です。

```mermaid
flowchart TB
    U[ユーザー入力] --> A[1. User Context / Intent Input]
    A --> B[2. User Meaning Estimation]
    B --> C[3. Hard Filter]
    C --> D[4. Candidate Retrieval]
    D --> E[5. Meaning Matching]
    E --> F[6. Final Ranking]
    F --> G[7. Recommendation Result]
    G --> H[8. Explanation Generation]
    G --> I[9. User Action Logging]

    subgraph InputLayer[入力レイヤ]
        A
    end

    subgraph MeaningLayer[意味推定レイヤ]
        B
    end

    subgraph RetrievalLayer[候補生成レイヤ]
        C
        D
    end

    subgraph RankingLayer[評価・順位付けレイヤ]
        E
        F
    end

    subgraph OutputLayer[出力・学習レイヤ]
        G
        H
        I
    end

    J[Relationship / Occasion Rules] --> B
    K[Hint Dictionary / Semantic Concept] --> B
    L[Item Meaning Store] --> D
    L --> E
    M[Popularity / Risk Signals] --> F
    N[Recommendation Logs / Evaluation Data] --> O[10. Offline Evaluation / Tuning]
    I --> N
    O --> J
    O --> K
    O --> L
    O --> M
```

---

# 1. この図の見方

## 事実

このアーキテクチャは、推薦を次の流れで捉えています。

1. ユーザー入力を受ける
2. ユーザー意図を Meaning に変換する
3. 候補商品を絞る
4. 商品とユーザーの Meaning を照合する
5. popularity / risk も加味して最終順位を出す
6. 結果を返す
7. ログを蓄積して改善に回す

## 推論

今回のサービスの本質は、

**「検索条件に一致する商品を探す」のではなく、「贈答意図に意味的に合う商品を選ぶ」**

ことです。

なので、通常のEC検索アーキテクチャよりも、中央にあるべきなのは

- 商品マスタ
- キーワード検索

ではなく、

- **User Meaning Estimation**
- **Item Meaning Store**
- **Meaning Matching**

です。

---

# 2. 各モジュールの役割

---

## 2-1. 1. User Context / Intent Input

### 役割

ユーザーから推薦に必要な入力を受け取る部分です。

### 主な入力

- relationship
- occasion
- 好み特徴
- 避けたい特徴
- 予算
- NG条件

### 補足

ここではまだ「商品」は決めません。

まず集めるのは **贈答文脈** です。

---

## 2-2. 2. User Meaning Estimation

### 役割

ユーザー入力を、8つの Feature に変換します。

### 出力

- `resolved_feature`
- `user_social`
- `user_symbolic`
- `λ_ctx`

### 内部で使うもの

- `gift_context_relationship_rule`
- `gift_context_occasion_rule`
- `gift_context_pair_rule`
- `gift_context_resolved_feature`
- Semantic Concept / Hint Dictionary

### イメージ

たとえば、

- 上司へのお礼
- 失礼がない
- 少し特別感もほしい

という入力から、

- formality 高め
- safety 高め
- brand_appropriateness 高め
- novelty は少しだけ
- emotion は中程度

のようなユーザー側 Meaning を作ります。

---

## 2-3. 3. Hard Filter

### 役割

推薦以前に、明確に除外すべき条件で候補を削る層です。

### 例

- 予算外
- NGカテゴリ
- 在庫なし
- 配送不可
- 性別/年齢不整合
- 明示NG特徴

### 補足

ここは Meaning Matching の前段です。

意味的に良くても、条件違反の商品はここで落とします。

---

## 2-4. 4. Candidate Retrieval

### 役割

全商品から、意味的に近そうな商品候補を粗く抽出する層です。

### 入力

- user meaning
- 必要に応じて semantic query

### 出力

- 上位N件の候補集合

### 実装候補

- embedding類似検索
- semantic concept ベース検索
- item meaning の近傍検索

### 補足

ここではまだ最終順位は決めません。

目的は **全件比較を避けるための候補絞り込み** です。

---

## 2-5. 5. Meaning Matching

### 役割

候補商品に対して、ユーザーとの一致度を詳細に計算する層です。

### 計算対象

- featureごとの距離
- social_match
- symbolic_match

### 既存整理との対応

- `distance_f = |user_f - item_f|`
- `match_f = 1 - distance_f`
- `social_match = mean(...)`
- `symbolic_match = mean(...)`

### 補足

ここはこのサービスの中核です。

商品そのものの性質ではなく、**「ユーザーに対してどれだけ合うか」** を計算します。

---

## 2-6. 6. Final Ranking

### 役割

Matching結果に popularity / risk / 文脈重みを加味して最終順位を出す層です。

### 主な要素

- `context_score`
- `popularity`
- `risk`
- `λ_ctx`

### 既存整理との対応

```
final_score
= context_score
+ (1 - λ_ctx) * popularity
- (1 - λ_ctx) * risk
```

### 補足

ここで「無難さ寄り」か「特別感寄り」かの調整が入ります。

つまり、

- `λ_ctx` が低い → popularity / risk を重めに使う
- `λ_ctx` が高い → 意味一致をより重く見る

です。

---

## 2-7. 7. Recommendation Result

### 役割

最終的にユーザーへ提示する推薦結果を生成する層です。

### 出力例

- 推薦商品一覧
- 順位
- スコア
- 推薦理由の元情報

---

## 2-8. 8. Explanation Generation

### 役割

「なぜこの商品を勧めたのか」を説明文として出す層です。

### 説明例

- 上司向けでも失礼がなく、安心感が高い
- 定番すぎず、ほどよい特別感がある
- お礼ギフトとして文脈に合っている

### 補足

これは後から改善可能ですが、アーキテクチャ上は最初から箱を用意したほうがよいです。

理由は、**evidence保持の必要性** がここで発生するからです。

---

## 2-9. 9. User Action Logging

### 役割

推薦結果に対するユーザー行動を記録する層です。

### ログ例

- 表示された候補
- クリックした商品
- お気に入り追加
- 離脱
- 再検索
- 条件変更

### 補足

これは将来の改善の土台です。

MVPでは簡易でもよいですが、最終系では非常に重要です。

---

## 2-10. 10. Offline Evaluation / Tuning

### 役割

ログや評価データを使って、推薦精度や心理モデルを改善する層です。

### 改善対象

- relationship / occasion rule
- hint dictionary
- semantic concept
- item meaning 抽出
- popularity / risk パラメータ
- final ranking 重み

### 補足

ここがあることで、アーキテクチャが「一回作って終わり」ではなく、

**検証可能な推薦システム** になります。

---

# 3. アーキテクチャを機能群で分けるとこうなる

整理しやすいように、機能群で見ると次です。

| 機能群     | 主なモジュール                                   |
| ---------- | ------------------------------------------------ |
| 入力処理   | User Context / Intent Input                      |
| 意味推定   | User Meaning Estimation, Item Meaning Extraction |
| 候補生成   | Hard Filter, Candidate Retrieval                 |
| 精密評価   | Meaning Matching, Final Ranking                  |
| 出力       | Recommendation Result, Explanation               |
| 観測・改善 | Logging, Offline Evaluation                      |

---

# 4. この図から見えてくる重要設計論点

---

## 論点1: `Item Meaning Store` は独立モジュール

### 事実

図の中で `Item Meaning Store` は Candidate Retrieval と Meaning Matching の両方から参照されています。

### 推論

つまり `item_meaning` は単なる補助データではなく、**推薦基盤の中心ストア** です。

このため、商品マスタの付属列ではなく、独立管理の考え方は妥当です。

---

## 論点2: ルール群も独立資産

### 事実

Relationship / Occasion Rules や Hint Dictionary は User Meaning Estimation に入力されています。

### 推論

これらはアプリのコードに埋めるより、

**データとして管理・改善できる構造** にしたほうがよいです。

---

## 論点3: ログ設計が必須

### 事実

Offline Evaluation / Tuning は Recommendation Logs に依存しています。

### 推論

後で精度改善するなら、

**推薦を出すだけでなく、推薦過程と結果を観測できること**

が必要です。

---

# 5. MVPと最終系の差分も、この図で見える

---

## MVPでまず必要な部分

- User Input
- User Meaning Estimation
- Hard Filter
- Candidate Retrieval
- Meaning Matching
- Final Ranking
- Recommendation Result

## MVPでは簡易でよい部分

- Explanation Generation
- User Action Logging
- Offline Evaluation / Tuning

## 最終系で強化する部分

- 説明生成の自然文品質
- 行動ログによる改善
- A/Bテスト
- 重み自動調整
- 人手評価データとの突合

---

# 6. このあと作るべき成果物

この T1 を作ったので、次は自然に以下へ進めます。

## T2

**モジュール定義 / 機能一覧**

作る内容:

- 各モジュールの責務
- 入出力
- MVP対象か
- バッチかオンラインか

## T3

**MVP〜最終系ロードマップ**

作る内容:

- Phase1〜PhaseN
- どこまでを先に実装するか
- 何を後回しにするか

## T4

**テスト・検証方針**

作る内容:

- 各モジュールをどう評価するか
- 何を保存する必要があるか

---

# 7. 今回のT1の要点まとめ

## 事実

このサービスの全体像は、

- ユーザー意図を Meaning に変換し
- 商品の Meaning と照合し
- popularity / risk も加味して
- 推薦結果を出し
- ログを蓄積して改善する

という構造です。

## 推論

この構造を先に固定しておくことで、後続の

- テーブル定義
- JSON利用方針
- ログ設計
- テスト設計

がぶれにくくなります。
