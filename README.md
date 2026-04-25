# Gift Recommendation Service

## 1. 概要

本リポジトリは、Gift Recommendation Service（贈答意味ベースレコメンド）の実装・設計を管理する。

本サービスは以下の特徴を持つ：

- 検索ではなく「意味」に基づくレコメンド
- Gift Meaning モデル（Social × Symbolic）
- 2段階ランキング（retrieval → ranking）
- リスク許容度による制御
- Observability前提の設計（評価・改善可能）

---

## 2. 開発方針（重要）

本プロジェクトは以下の前提で開発する：

- 個人開発（MVP優先）
- AIエージェント前提（ChatGPT / Cursor）
- docs正本運用
- 将来の拡張・チーム開発を考慮

---

## 3. 正本管理（最重要）

### 正本

👉 `docs/` ディレクトリ

- すべての設計・仕様は docs を正本とする
- 実装は docs を入力として行う

---

### 副本

- Notion（閲覧・整理用）

---

### ルール

- docs未参照で実装しない
- 仕様変更は docs と同時に更新する

---

## 4. ディレクトリ構成

```text
.
├─ apps/
│  ├─ web/     # フロントエンド
│  ├─ api/     # APIサーバ
│  ├─ reco/    # レコメンドエンジン
│  └─ batch/   # ETL / バッチ処理
│
├─ packages/   # 共通ライブラリ
├─ docs/       # 設計ドキュメント（正本）
├─ .cursor/
│  └─ rules/   # AIエージェント制御ルール
└─ README.md
```

## 5. 各アプリの役割

| アプリ | 役割                |
| ------ | ------------------- |
| web    | UI / 入力 / 表示    |
| api    | 業務入口 / 調停     |
| reco   | レコメンドロジック  |
| batch  | ETL / 再計算 / 集計 |

---

## 6. アーキテクチャ原則

- Web / API / Reco / Batch 分離
- API を業務入口とする
- Reco にロジックを集約
- Batch で重処理を吸収
- docs を正本とする
- runId で追跡可能にする
- Observability を前提にする

---

## 7. 開発フロー

```
1. Issue作成
2. docs設計・更新
3. ブランチ作成
4. 実装（Cursor）
5. テスト
6. PR作成
7. マージ（develop → main）
```

---

## 8. Git運用

- 1 Issue = 1責務
- 1 PR = 1目的
- ブランチ命名：
  - feature/issue-xxx-\*
  - fix/issue-xxx-\*
- docs更新は同一PRで実施
- main は常にリリース可能状態を維持

---

## 9. AIエージェント運用

本プロジェクトでは Cursor を中心にAIを活用する。

### 役割

| ツール  | 役割           |
| ------- | -------------- |
| ChatGPT | 設計・レビュー |
| Cursor  | 実装・テスト   |

---

### ルール

- `.cursor/rules/` を必ず参照する
- docs を入力として実装する
- 推論で仕様を補完しない

---

## 10. Cursor Rules

主要ルール：

- response_style.mdc
- docs.mdc
- database.mdc
- observability.mdc
- architecture.mdc
- testing.mdc
- api.mdc
- batch.mdc
- frontend_ui.mdc
- git_github.mdc

---

## 11. セットアップ（開発準備中）

本プロジェクトは現在設計フェーズのため、
セットアップ手順は未確定。

実装フェーズで以下を定義予定：

- 各アプリの起動方法（web / api / reco / batch）
- 必要な環境変数
- DB接続設定
- Docker構成（必要な場合）
- ローカル開発フロー

---

## 12. 品質方針

- 動くだけでなく「追える」ことを重視
- Observability前提
- MVPでは重点集中テスト
- スコアロジックは特に厳密に扱う

---

## 13. 注意事項

### やってはいけないこと

- docs未参照で実装する
- 仕様変更をコードだけで行う
- RecoロジックをAPIやUIに持ち込む
- 冪等性のないBatchを作る
- 観測できない処理を作る

---

## 14. 一言まとめ

👉 このリポジトリは「コード置き場」ではなく

👉 「設計を正本として実装を制御する環境」である
