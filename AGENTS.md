# AGENTS.md

---

# 1. Project Overview

## 1.1 System Name

Gift Recommendation Service

## 1.2 Purpose

ユーザーの入力条件から「意味ベース」でギフトを推薦するレコメンドシステム

---

# 2. Core Architecture

## 2.1 System Components

- Web
- API
- Reco
- Batch

👉 コンポーネントは明確に分離すること

---

## 2.2 Recommendation Architecture

- 2段階ランキング
  - Candidate Retrieval（Embedding）
  - Meaning-based Ranking
- MMRによる多様性制御

---

## 2.3 Gift Meaning Model

### 構造

- Social
- Symbolic

👉 すべての推薦ロジックはこの空間に基づく

---

## ❗重要制約

- conformityは使用しない
- Social / Symbolicのみ使用する

---

# 3. Data Design Principles

---

## 3.1 基本方針

- 正本は最小限にする
- 派生データは用途別に分離
- 再計算可能な構造を維持
- run単位で再現可能にする

---

## 3.2 重要ルール

- item_embeddingは永続化する
- user_embeddingはキャッシュ扱い
- recommendation_runを中心に全データを紐づける

---

## 3.3 Versioning

- semantic_config と semantic_config_version を分離
- semantic_config_version は「利用バージョン指定」
- model_version を明示的に管理

---

# 4. Observability Principles

---

## 4.1 目的

- 障害検知ではなく「改善可能性の確保」

---

## 4.2 監視レイヤ

- System
- Application
- Business
- Model

---

## 4.3 必須要件

- runIdトレース必須
- API横断ログ
- 分布監視（μ / σ / p95）
- メトリクス収集

---

## ❗重要

ObservabilityはMVPでも必須機能とする

---

# 5. Development Principles

---

## 5.1 開発方針

- MVP高速開発
- ただし壊れない最小構成を維持

---

## 5.2 設計原則

- 設計を入力に実装する
- コードから仕様を作らない
- 暗黙仕様禁止

---

## 5.3 実装原則

- 1変更1目的
- 小さく変更する
- docsとコードを必ず一致させる

---

# 6. Docs as Source of Truth

---

## 6.1 正本

👉 docs/ ディレクトリが唯一の正本

---

## 6.2 ルール

- 設計変更時はdocs更新必須
- docsなしの仕様変更は禁止
- Notionは副本

---

## 6.3 AI利用時のルール

- 必ずdocsを参照してから生成する
- docsと矛盾する生成は禁止

---

# 7. AI Usage Policy

---

## 7.1 役割

| 領域   | 担当             |
| ------ | ---------------- |
| 設計   | ChatGPT + Cursor |
| 実装   | Cursor           |
| テスト | Cursor           |
| 判断   | Human            |

---

## 7.2 原則

- AIは加速手段
- 品質保証は人間

---

## 7.3 禁止事項

- docs未参照での生成
- 一括生成
- 不明な仕様の推測実装

---

# 8. Testing Principles

---

## 8.1 方針

- 重点テスト
- 全網羅は不要

---

## 8.2 重点対象

- レコメンドスコア
- API入出力
- DB更新
- Batch処理

---

## 8.3 Observabilityテスト

- runId追跡可能
- メトリクス出力
- 分布確認可能

---

# 9. CI/CD Principles

---

## 9.1 方針

- CI = 品質ゲート
- CD = 安全なリリース

---

## 9.2 必須条件

- build成功
- test成功
- API確認
- Observability成立

---

# 10. Branch / Issue Rules

---

## 10.1 原則

- 1Issue = 1責務
- 1PR = 1目的

---

## 10.2 命名

- feature/issue-xxx
- fix/issue-xxx

---

# 11. Critical Rules（最重要）

---

以下は必ず守ること：

- docsとコードの乖離禁止
- 設計書未参照での実装禁止
- conformityを使用しない
- runIdトレース必須
- semantic_config_version / model_versionを必ず考慮
- Observabilityを省略しない

---

# 12. Summary

このプロジェクトは：

👉  
**「意味ベースレコメンド × 高観測性 × 再現性重視」**

のシステムである

---

👉  
AIは「正本docsを読ませて制御する」こと

---
