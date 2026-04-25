# F01：推薦条件入力受付（M01）

## ■ 概要

ユーザーから推薦条件を受け取る。

## ■ 入力

- relationship
- occasion
- price_range
- desired_condition
- non_desired_condition
- ng_condition

## ■ 出力

- raw_input

## ■ 処理

- 入力受付
- 必須チェック

---

# F02：入力値正規化（M01）

## ■ 概要

入力を後続処理用に正規化

## ■ 入力

- raw_input

## ■ 出力

- normalized_input

## ■ 処理

- relationship/occasionコード化
- price正規化
- NG条件構造化
- 形態素解析

---

# F03：User feature推定（M02）

※前回提示内容を統合

---

# F04：λ_ctx算出（M02）

## ■ 概要

Social / Symbolicバランス係数を算出

## ■ 入力

- user_social
- user_symbolic

## ■ 出力

- λ_ctx

## ■ 処理

```
λ_ctx =
  user_symbolic / (user_social + user_symbolic + ε)
```

---

# F05：明示条件フィルタ（M03）

## ■ 概要

NG条件・価格条件で除外

## ■ 入力

- normalized_input
- item

## ■ 出力

- filtered_items

## ■ 処理

- price条件
- ng_genre
- ng_tag

---

# F06：候補商品抽出（M04）

※前回整理を採用（方式B）

---

# F07：feature一致度計算（M05）

## ■ 概要

user × item のfeature距離算出

## ■ 入力

- user_feature
- item_feature

## ■ 出力

- feature_match

## ■ 処理

```
match_f = 1 - |user_f - item_f|
```

---

# F08：social/symbolic一致度集約（M05）

## ■ 概要

feature一致度を集約

## ■ 入力

- feature_match

## ■ 出力

- social_match
- symbolic_match

---

# F09：最終スコア算出（M06）

※前回整理を統合

---

# F10：推薦結果整形（M07）

## ■ 概要

APIレスポンス生成

## ■ 入力

- ranked_items

## ■ 出力

- recommendation_result

---

# F11：推薦理由表示（M08）

## ■ 概要

理由ラベル生成

## ■ 入力

- feature_match
- context_score

## ■ 出力

- reason_tags

## ■ MVP

- テンプレート

---

# F12：推薦表示ログ記録（M09）

## ■ 概要

表示ログ記録

## ■ 入力

- recommendation_result

## ■ 出力

- impression_log

---

# F13：クリックログ記録（M09）

## ■ 概要

クリックログ記録

## ■ 入力

- click_event

## ■ 出力

- click_log

---

# F14：商品meaning抽出（M11）

※前回整理（辞書→ルール→統合）採用

---

# F15：semantic concept管理（M12）

## ■ 概要

concept / 辞書管理

## ■ 入力

- concept定義
- keyword辞書

## ■ 出力

- version付きconcept

---

# F16：version管理（M13）

## ■ 概要

ロジックバージョン管理

## ■ 入力

- rule_version
- prompt_version

## ■ 出力

- version_id

---

# F17：手動評価比較（M10/M14）

## ■ 概要

人手評価による比較

## ■ 入力

- recommendation_result
- evaluation_case

## ■ 出力

- human_feedback

---

# F18：オフライン評価（M10）

## ■ 概要

精度検証

## ■ 入力

- logs
- dataset

## ■ 出力

- metrics

---

# F19：説明生成高度化（M08）

## ■ 概要

LLMによる説明生成

## ■ 入力

- feature_match
- context

## ■ 出力

- explanation_text

---

# F20：行動ログ分析（M09/M10）

## ■ 概要

ログ分析

## ■ 入力

- user_logs

## ■ 出力

- insights

---

# F21：A/Bテスト（M10）

## ■ 概要

バージョン比較

## ■ 入力

- version_A
- version_B

## ■ 出力

- comparison_result
