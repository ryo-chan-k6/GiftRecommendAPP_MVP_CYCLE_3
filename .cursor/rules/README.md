# Cursor Rules Overview

## 1. 目的

本ディレクトリは、AIエージェント（Cursor）が本プロジェクトの設計・実装ルールに従って動作するための制御ルールを定義する。

本READMEは以下を明確にする：

- 各ルールの役割
- 適用範囲
- 優先順位
- 利用方法

---

## 2. 基本方針（最重要）

### MUST

- MUST docs を正本として扱う
- MUST rules を前提として実装する
- MUST 推測で仕様を補完しない

---

### 最重要ルール

👉 docsを読まずに作るな  
👉 rulesに違反する実装をするな

---

## 3. ルール一覧

| ルール             | 役割             | 防ぐもの               |
| ------------------ | ---------------- | ---------------------- |
| response_style.mdc | 回答スタイル制御 | 曖昧な回答・推論混在   |
| docs.mdc           | docs正本強制     | 設計未参照             |
| database.mdc       | DB設計統制       | テーブル抜け・整合崩れ |
| observability.mdc  | 観測強制         | 見えない処理           |
| architecture.mdc   | 構造制御         | 責務崩壊・依存違反     |
| testing.mdc        | テスト統制       | 未検証変更             |
| api.mdc            | API設計統制      | API不整合              |
| batch.mdc          | バッチ統制       | 冪等性崩壊             |
| frontend_ui.mdc    | UI統制           | 仕様乖離UI             |
| git_github.mdc     | Git運用統制      | 管理崩壊               |

---

## 4. 優先順位

ルールが競合した場合の優先順位：

1. docs.mdc
2. architecture.mdc
3. database.mdc
4. api.mdc / batch.mdc / frontend_ui.mdc
5. observability.mdc
6. testing.mdc
7. git_github.mdc
8. response_style.mdc

---

## 5. 適用タイミング

### 設計時

- docs.mdc
- architecture.mdc
- database.mdc
- api.mdc
- batch.mdc

---

### 実装時

- architecture.mdc
- api.mdc
- batch.mdc
- frontend_ui.mdc
- observability.mdc

---

### テスト時

- testing.mdc
- observability.mdc

---

### 運用 / 管理

- git_github.mdc

---

### 常時適用

- response_style.mdc
- docs.mdc

---

## 6. ルールの使い分け

### 迷った場合

- 仕様 → docs.mdc
- 構造 → architecture.mdc
- データ → database.mdc
- API → api.mdc
- バッチ → batch.mdc
- UI → frontend_ui.mdc
- 観測 → observability.mdc
- テスト → testing.mdc
- Git → git_github.mdc

---

## 7. 典型的なミスと対応ルール

| ミス            | 対応ルール        |
| --------------- | ----------------- |
| docs未参照      | docs.mdc          |
| テーブル抜け    | database.mdc      |
| APIズレ         | api.mdc           |
| 冪等性なしBatch | batch.mdc         |
| UI仕様違反      | frontend_ui.mdc   |
| ログ不足        | observability.mdc |
| 未テスト変更    | testing.mdc       |
| 構造崩壊        | architecture.mdc  |

---

## 8. 運用ルール

### MUST

- MUST 新しい設計ルールはここに追加する
- MUST 既存ルールと重複しないようにする
- MUST ルールの責務を明確にする

---

### SHOULD

- SHOULD ルールは小さく分割する
- SHOULD 1ルール1責務にする

---

## 9. 変更時ルール

### MUST

- MUST ルール変更時は影響範囲を確認する
- MUST docs と整合する

---

## 10. 一言まとめ

👉 rules は「AIの振る舞いを固定する設計書」である  
👉 docs と rules が揃って初めて開発が成立する
